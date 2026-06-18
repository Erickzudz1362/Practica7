from fastapi import Depends, FastAPI
from pydantic import BaseModel

from common.db import connect, row_to_dict, rows_to_dicts
from common.security import current_user


app = FastAPI(title="Notification Service", version="1.0.0")
db = connect("notification.db")


class EventIn(BaseModel):
    type: str
    payload: dict
    occurred_at: str


class NotificationIn(BaseModel):
    customer_id: int | None = None
    channel: str = "WHATSAPP"
    content: str


def init_db():
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            payload TEXT NOT NULL,
            occurred_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER,
            channel TEXT NOT NULL,
            content TEXT NOT NULL,
            event_type TEXT,
            created_at TEXT NOT NULL
        );
        """
    )
    db.commit()


init_db()


def notification_from_event(event: EventIn):
    payload = event.payload
    if event.type == "SaleCompleted":
        return {
            "customer_id": payload.get("customer_id"),
            "channel": "WHATSAPP",
            "content": f"Venta completada. Total Bs {payload.get('total', 0):.2f}. Gracias por su compra.",
        }
    if event.type == "TransferCompleted":
        return {"customer_id": None, "channel": "PUSH", "content": "Transferencia de inventario completada."}
    if event.type == "PointsAssigned":
        customer = payload.get("customer", {})
        return {
            "customer_id": customer.get("id"),
            "channel": "SMS",
            "content": f"Se asignaron {payload.get('points', 0)} puntos a su cuenta.",
        }
    if event.type == "StockLow":
        return {"customer_id": None, "channel": "PUSH", "content": "Alerta: producto con stock bajo."}
    if event.type == "PromotionCreated":
        return {"customer_id": payload.get("customer_id"), "channel": "EMAIL", "content": "Nueva promoción disponible."}
    return None


@app.get("/health")
def health():
    return {"status": "ok", "service": "notification-service"}


@app.post("/events")
def consume_event(event: EventIn):
    import json

    db.execute(
        "INSERT INTO events(event_type, payload, occurred_at) VALUES (?, ?, ?)",
        (event.type, json.dumps(event.payload, ensure_ascii=False), event.occurred_at),
    )
    notification = notification_from_event(event)
    if notification:
        db.execute(
            """
            INSERT INTO notifications(customer_id, channel, content, event_type, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                notification["customer_id"],
                notification["channel"],
                notification["content"],
                event.type,
                event.occurred_at,
            ),
        )
    db.commit()
    return {"message": "Evento consumido", "notification_created": bool(notification)}


@app.post("/notifications", dependencies=[Depends(current_user)])
def create_notification(request: NotificationIn):
    cur = db.execute(
        """
        INSERT INTO notifications(customer_id, channel, content, event_type, created_at)
        VALUES (?, ?, ?, ?, datetime('now'))
        """,
        (request.customer_id, request.channel, request.content, "MANUAL"),
    )
    db.commit()
    return row_to_dict(db.execute("SELECT * FROM notifications WHERE id = ?", (cur.lastrowid,)).fetchone())


@app.get("/notifications", dependencies=[Depends(current_user)])
def list_notifications():
    return rows_to_dicts(db.execute("SELECT * FROM notifications ORDER BY id DESC").fetchall())


@app.get("/events", dependencies=[Depends(current_user)])
def list_events():
    return rows_to_dicts(db.execute("SELECT * FROM events ORDER BY id DESC").fetchall())
