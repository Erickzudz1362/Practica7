import os
from datetime import date, datetime, timezone

import requests
from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from common.db import connect, row_to_dict, rows_to_dicts
from common.events import publish_event
from common.security import current_user


app = FastAPI(title="Sales Service", version="1.0.0")
db = connect("sales.db")

PRODUCT_URL = os.getenv("PRODUCT_URL", "http://127.0.0.1:8002")
INVENTORY_URL = os.getenv("INVENTORY_URL", "http://127.0.0.1:8003")
CUSTOMER_URL = os.getenv("CUSTOMER_URL", "http://127.0.0.1:8004")


class SaleItemIn(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0)
    unit_price: float | None = Field(None, gt=0)


class SaleIn(BaseModel):
    customer_id: int
    branch_id: int
    payment_method: str = Field("EFECTIVO", examples=["EFECTIVO", "TARJETA"])
    items: list[SaleItemIn]


def init_db():
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            branch_id INTEGER NOT NULL,
            payment_method TEXT NOT NULL,
            total REAL NOT NULL,
            status TEXT NOT NULL,
            invoice_number TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS sale_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            subtotal REAL NOT NULL,
            FOREIGN KEY(sale_id) REFERENCES sales(id)
        );
        """
    )
    db.commit()


init_db()


def now():
    return datetime.now(timezone.utc).isoformat()


def auth_headers(request: Request):
    return {"Authorization": request.headers.get("Authorization", "")}


def service_get(url: str, request: Request):
    response = requests.get(url, headers=auth_headers(request), timeout=5)
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()


def service_post(url: str, body: dict, request: Request):
    response = requests.post(url, json=body, headers=auth_headers(request), timeout=5)
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()


@app.get("/health")
def health():
    return {"status": "ok", "service": "sales-service"}


@app.post("/sales", dependencies=[Depends(current_user)])
def create_sale(sale: SaleIn, request: Request):
    if not sale.items:
        raise HTTPException(status_code=400, detail="La venta debe tener al menos un producto")

    detailed_items = []
    total = 0.0
    for item in sale.items:
        product = service_get(f"{PRODUCT_URL}/products/{item.product_id}", request)
        stock_rows = service_get(f"{INVENTORY_URL}/inventory/{item.product_id}", request)
        branch_stock = next((row for row in stock_rows if row["branch_id"] == sale.branch_id), None)
        if not branch_stock or branch_stock["quantity"] < item.quantity:
            raise HTTPException(status_code=409, detail=f"Stock insuficiente para producto {item.product_id}")
        unit_price = item.unit_price or branch_stock["sale_price"] or product["base_price"]
        subtotal = round(unit_price * item.quantity, 2)
        detailed_items.append(
            {
                "product_id": item.product_id,
                "product_name": product["name"],
                "quantity": item.quantity,
                "unit_price": unit_price,
                "subtotal": subtotal,
            }
        )
        total += subtotal

    invoice_number = f"FAC-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    cur = db.execute(
        """
        INSERT INTO sales(customer_id, branch_id, payment_method, total, status, invoice_number, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (sale.customer_id, sale.branch_id, sale.payment_method, round(total, 2), "CREATED", invoice_number, now()),
    )
    sale_id = cur.lastrowid
    for item in detailed_items:
        db.execute(
            """
            INSERT INTO sale_items(sale_id, product_id, product_name, quantity, unit_price, subtotal)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (sale_id, item["product_id"], item["product_name"], item["quantity"], item["unit_price"], item["subtotal"]),
        )
    db.commit()
    publish_event("SaleCreated", {"sale_id": sale_id, "customer_id": sale.customer_id, "total": round(total, 2)})

    for item in detailed_items:
        service_post(
            f"{INVENTORY_URL}/inventory/reserve",
            {
                "product_id": item["product_id"],
                "branch_id": sale.branch_id,
                "quantity": item["quantity"],
                "reason": str(sale_id),
            },
            request,
        )

    points = int(total // 10)
    if points > 0:
        service_post(
            f"{CUSTOMER_URL}/customers/{sale.customer_id}/points",
            {"points": points, "reason": "Puntos por venta", "sale_id": sale_id},
            request,
        )

    db.execute("UPDATE sales SET status = ? WHERE id = ?", ("COMPLETED", sale_id))
    db.commit()
    result = get_sale(sale_id)
    publish_event("SaleCompleted", result)
    return result


@app.get("/sales", dependencies=[Depends(current_user)])
def list_sales():
    return rows_to_dicts(db.execute("SELECT * FROM sales ORDER BY id DESC").fetchall())


@app.get("/sales/report/daily", dependencies=[Depends(current_user)])
def daily_report(day: date | None = None):
    selected = (day or date.today()).isoformat()
    rows = rows_to_dicts(
        db.execute(
            """
            SELECT s.payment_method, si.product_name, si.quantity, si.unit_price, si.subtotal
            FROM sale_items si
            JOIN sales s ON s.id = si.sale_id
            WHERE date(s.created_at) = ? AND s.status = 'COMPLETED'
            ORDER BY s.payment_method, si.id
            """,
            (selected,),
        ).fetchall()
    )
    by_payment = {}
    for row in rows:
        by_payment.setdefault(row["payment_method"], {"total": 0, "items": []})
        by_payment[row["payment_method"]]["total"] += row["subtotal"]
        by_payment[row["payment_method"]]["items"].append(row)
    return {
        "date": selected,
        "total_income": round(sum(row["subtotal"] for row in rows), 2),
        "payments": by_payment,
    }


@app.get("/sales/{sale_id}", dependencies=[Depends(current_user)])
def get_sale(sale_id: int):
    sale = row_to_dict(db.execute("SELECT * FROM sales WHERE id = ?", (sale_id,)).fetchone())
    if not sale:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    items = rows_to_dicts(db.execute("SELECT * FROM sale_items WHERE sale_id = ? ORDER BY id", (sale_id,)).fetchall())
    sale["items"] = items
    sale["receipt"] = {
        "invoice_number": sale["invoice_number"],
        "customer_id": sale["customer_id"],
        "branch_id": sale["branch_id"],
        "total": sale["total"],
        "status": sale["status"],
    }
    return sale


@app.post("/sales/{sale_id}/cancel", dependencies=[Depends(current_user)])
def cancel_sale(sale_id: int):
    sale = db.execute("SELECT * FROM sales WHERE id = ?", (sale_id,)).fetchone()
    if not sale:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    db.execute("UPDATE sales SET status = ? WHERE id = ?", ("CANCELLED", sale_id))
    db.commit()
    payload = row_to_dict(sale) | {"status": "CANCELLED"}
    publish_event("SaleCancelled", payload)
    return payload
