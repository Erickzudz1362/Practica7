from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from common.db import connect, row_to_dict, rows_to_dicts
from common.events import publish_event
from common.security import current_user


app = FastAPI(title="Product Service", version="1.0.0")
db = connect("product.db")


class CategoryIn(BaseModel):
    name: str


class ProductIn(BaseModel):
    name: str = Field(..., examples=["Leche Pil 980cc"])
    category_id: int | None = None
    brand: str | None = Field(None, examples=["Pil"])
    barcode: str | None = Field(None, examples=["779000000001"])
    base_price: float = Field(..., gt=0, examples=[18.50])
    status: str = "ACTIVE"


def init_db():
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category_id INTEGER,
            brand TEXT,
            barcode TEXT UNIQUE,
            base_price REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'ACTIVE',
            FOREIGN KEY(category_id) REFERENCES categories(id)
        );
        """
    )
    for category in ["Abarrotes", "Lácteos", "Limpieza", "Bebidas"]:
        db.execute("INSERT OR IGNORE INTO categories(name) VALUES (?)", (category,))
    db.commit()


init_db()


@app.get("/health")
def health():
    return {"status": "ok", "service": "product-service"}


@app.post("/categories", dependencies=[Depends(current_user)])
def create_category(request: CategoryIn):
    db.execute("INSERT OR IGNORE INTO categories(name) VALUES (?)", (request.name,))
    db.commit()
    return row_to_dict(db.execute("SELECT * FROM categories WHERE name = ?", (request.name,)).fetchone())


@app.get("/categories", dependencies=[Depends(current_user)])
def list_categories():
    return rows_to_dicts(db.execute("SELECT * FROM categories ORDER BY name").fetchall())


@app.post("/products", dependencies=[Depends(current_user)])
def create_product(request: ProductIn):
    try:
        cur = db.execute(
            """
            INSERT INTO products(name, category_id, brand, barcode, base_price, status)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (request.name, request.category_id, request.brand, request.barcode, request.base_price, request.status),
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Producto duplicado o datos inválidos") from exc
    db.commit()
    product = row_to_dict(db.execute("SELECT * FROM products WHERE id = ?", (cur.lastrowid,)).fetchone())
    publish_event("ProductCreated", product)
    return product


@app.get("/products", dependencies=[Depends(current_user)])
def list_products():
    rows = db.execute(
        """
        SELECT p.*, c.name AS category_name
        FROM products p LEFT JOIN categories c ON c.id = p.category_id
        ORDER BY p.id
        """
    ).fetchall()
    return rows_to_dicts(rows)


@app.get("/products/{product_id}", dependencies=[Depends(current_user)])
def get_product(product_id: int):
    row = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return row_to_dict(row)


@app.put("/products/{product_id}", dependencies=[Depends(current_user)])
def update_product(product_id: int, request: ProductIn):
    if not db.execute("SELECT id FROM products WHERE id = ?", (product_id,)).fetchone():
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    db.execute(
        """
        UPDATE products
        SET name = ?, category_id = ?, brand = ?, barcode = ?, base_price = ?, status = ?
        WHERE id = ?
        """,
        (request.name, request.category_id, request.brand, request.barcode, request.base_price, request.status, product_id),
    )
    db.commit()
    product = row_to_dict(db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone())
    publish_event("ProductUpdated", product)
    return product


@app.delete("/products/{product_id}", dependencies=[Depends(current_user)])
def delete_product(product_id: int):
    row = db.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    db.execute("DELETE FROM products WHERE id = ?", (product_id,))
    db.commit()
    publish_event("ProductDeleted", row_to_dict(row))
    return {"message": "Producto eliminado"}
