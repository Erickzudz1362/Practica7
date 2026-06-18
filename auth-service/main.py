from fastapi import Depends, FastAPI, HTTPException
from passlib.context import CryptContext
from pydantic import BaseModel, Field

from common.db import connect, row_to_dict, rows_to_dicts
from common.security import create_token, current_user


app = FastAPI(title="Authentication Service", version="1.0.0")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
db = connect("auth.db")


class LoginRequest(BaseModel):
    username: str = Field(..., examples=["admin"])
    password: str = Field(..., examples=["admin123"])


class UserCreate(BaseModel):
    username: str
    password: str
    roles: list[str] = ["CAJERO"]


def init_db():
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            roles TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1
        )
        """
    )
    exists = db.execute("SELECT id FROM users WHERE username = ?", ("admin",)).fetchone()
    if not exists:
        db.execute(
            "INSERT INTO users(username, password_hash, roles) VALUES (?, ?, ?)",
            ("admin", pwd_context.hash("admin123"), "ADMINISTRADOR,GERENTE,SUPERVISOR,CAJERO"),
        )
    db.commit()


init_db()


@app.get("/health")
def health():
    return {"status": "ok", "service": "auth-service"}


@app.post("/auth/login")
def login(request: LoginRequest):
    user = db.execute("SELECT * FROM users WHERE username = ? AND active = 1", (request.username,)).fetchone()
    if not user or not pwd_context.verify(request.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Credenciales inválidas")
    roles = [role.strip() for role in user["roles"].split(",") if role.strip()]
    return {"access_token": create_token(user["username"], roles), "token_type": "bearer", "roles": roles}


@app.post("/auth/users", dependencies=[Depends(current_user)])
def create_user(request: UserCreate):
    try:
        db.execute(
            "INSERT INTO users(username, password_hash, roles) VALUES (?, ?, ?)",
            (request.username, pwd_context.hash(request.password), ",".join(request.roles)),
        )
        db.commit()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="No se pudo crear el usuario") from exc
    return {"message": "Usuario creado"}


@app.get("/auth/users", dependencies=[Depends(current_user)])
def list_users():
    rows = db.execute("SELECT id, username, roles, active FROM users ORDER BY id").fetchall()
    return rows_to_dicts(rows)


@app.get("/auth/me")
def me(user=Depends(current_user)):
    return user
