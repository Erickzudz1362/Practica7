from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field

from common.db import connect, row_to_dict, rows_to_dicts
from common.events import publish_event
from common.security import current_user


app = FastAPI(title="Customer Service", version="1.0.0")
db = connect("customer.db")


class CustomerIn(BaseModel):
    full_name: str = Field(..., examples=["Juanito Pérez"])
    document: str | None = None
    email: EmailStr | None = None
    phone: str | None = None


class PointsIn(BaseModel):
    points: int
    reason: str = "COMPRA"
    sale_id: int | None = None


def init_db():
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT NOT NULL,
            document TEXT,
            email TEXT,
            phone TEXT,
            points INTEGER NOT NULL DEFAULT 0,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS customer_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            description TEXT NOT NULL,
            points INTEGER NOT NULL DEFAULT 0,
            sale_id INTEGER,
            created_at TEXT NOT NULL,
            FOREIGN KEY(customer_id) REFERENCES customers(id)
        );
        """
    )
    db.commit()


init_db()


def now():
    return datetime.now(timezone.utc).isoformat()


@app.get("/health")
def health():
    return {"status": "ok", "service": "customer-service"}


@app.post("/customers", dependencies=[Depends(current_user)])
def create_customer(request: CustomerIn):
    cur = db.execute(
        "INSERT INTO customers(full_name, document, email, phone, created_at) VALUES (?, ?, ?, ?, ?)",
        (request.full_name, request.document, request.email, request.phone, now()),
    )
    db.execute(
        "INSERT INTO customer_history(customer_id, event_type, description, created_at) VALUES (?, ?, ?, ?)",
        (cur.lastrowid, "CREATED", "Cliente registrado", now()),
    )
    db.commit()
    customer = row_to_dict(db.execute("SELECT * FROM customers WHERE id = ?", (cur.lastrowid,)).fetchone())
    publish_event("CustomerCreated", customer)
    return customer


@app.get("/customers", dependencies=[Depends(current_user)])
def list_customers():
    return rows_to_dicts(db.execute("SELECT * FROM customers ORDER BY id").fetchall())


@app.get("/customers/{customer_id}", dependencies=[Depends(current_user)])
def get_customer(customer_id: int):
    row = db.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return row_to_dict(row)


@app.get("/customers/{customer_id}/history", dependencies=[Depends(current_user)])
def customer_history(customer_id: int):
    if not db.execute("SELECT id FROM customers WHERE id = ?", (customer_id,)).fetchone():
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return rows_to_dicts(
        db.execute("SELECT * FROM customer_history WHERE customer_id = ? ORDER BY id", (customer_id,)).fetchall()
    )


@app.post("/customers/{customer_id}/points", dependencies=[Depends(current_user)])
def assign_points(customer_id: int, request: PointsIn):
    customer = db.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()
    if not customer:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    db.execute("UPDATE customers SET points = points + ? WHERE id = ?", (request.points, customer_id))
    db.execute(
        """
        INSERT INTO customer_history(customer_id, event_type, description, points, sale_id, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (customer_id, "POINTS_ASSIGNED", request.reason, request.points, request.sale_id, now()),
    )
    db.commit()
    updated = row_to_dict(db.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone())
    publish_event("PointsAssigned", {"customer": updated, "points": request.points, "sale_id": request.sale_id})
    return updated
