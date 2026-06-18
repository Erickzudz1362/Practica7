from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

from common.db import connect, row_to_dict, rows_to_dicts
from common.security import current_user


app = FastAPI(title="Company Service", version="1.0.0")
db = connect("company.db")


class CompanyIn(BaseModel):
    name: str
    nit: str | None = None


class CityIn(BaseModel):
    name: str


class BranchIn(BaseModel):
    company_id: int
    city_id: int | None = None
    name: str
    address: str | None = None


def init_db():
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            nit TEXT,
            active INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS cities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );
        CREATE TABLE IF NOT EXISTS branches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            city_id INTEGER,
            name TEXT NOT NULL,
            address TEXT,
            active INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY(company_id) REFERENCES companies(id),
            FOREIGN KEY(city_id) REFERENCES cities(id)
        );
        """
    )
    for city in ["Cochabamba", "La Paz", "Santa Cruz", "El Alto"]:
        db.execute("INSERT OR IGNORE INTO cities(name) VALUES (?)", (city,))
    db.commit()


init_db()


@app.get("/health")
def health():
    return {"status": "ok", "service": "company-service"}


@app.post("/companies", dependencies=[Depends(current_user)])
def create_company(request: CompanyIn):
    try:
        cur = db.execute("INSERT INTO companies(name, nit) VALUES (?, ?)", (request.name, request.nit))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="La compañía ya existe o los datos son inválidos") from exc
    db.commit()
    return row_to_dict(db.execute("SELECT * FROM companies WHERE id = ?", (cur.lastrowid,)).fetchone())


@app.get("/companies", dependencies=[Depends(current_user)])
def list_companies():
    return rows_to_dicts(db.execute("SELECT * FROM companies ORDER BY id").fetchall())


@app.get("/companies/{company_id}", dependencies=[Depends(current_user)])
def get_company(company_id: int):
    row = db.execute("SELECT * FROM companies WHERE id = ?", (company_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Compañía no encontrada")
    return row_to_dict(row)


@app.get("/cities", dependencies=[Depends(current_user)])
def list_cities():
    return rows_to_dicts(db.execute("SELECT * FROM cities ORDER BY name").fetchall())


@app.post("/cities", dependencies=[Depends(current_user)])
def create_city(request: CityIn):
    cur = db.execute("INSERT OR IGNORE INTO cities(name) VALUES (?)", (request.name,))
    db.commit()
    city = db.execute("SELECT * FROM cities WHERE name = ?", (request.name,)).fetchone()
    return row_to_dict(city)


@app.post("/branches", dependencies=[Depends(current_user)])
def create_branch(request: BranchIn):
    cur = db.execute(
        "INSERT INTO branches(company_id, city_id, name, address) VALUES (?, ?, ?, ?)",
        (request.company_id, request.city_id, request.name, request.address),
    )
    db.commit()
    return row_to_dict(db.execute("SELECT * FROM branches WHERE id = ?", (cur.lastrowid,)).fetchone())


@app.get("/branches", dependencies=[Depends(current_user)])
def list_branches(company_id: int | None = None):
    sql = """
        SELECT b.*, c.name AS company_name, ci.name AS city_name
        FROM branches b
        JOIN companies c ON c.id = b.company_id
        LEFT JOIN cities ci ON ci.id = b.city_id
    """
    params = ()
    if company_id:
        sql += " WHERE b.company_id = ?"
        params = (company_id,)
    sql += " ORDER BY b.id"
    return rows_to_dicts(db.execute(sql, params).fetchall())


@app.get("/branches/{branch_id}", dependencies=[Depends(current_user)])
def get_branch(branch_id: int):
    row = db.execute("SELECT * FROM branches WHERE id = ?", (branch_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Sucursal no encontrada")
    return row_to_dict(row)
