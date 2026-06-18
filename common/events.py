import os
from datetime import datetime, timezone

import requests


NOTIFICATION_URL = os.getenv("NOTIFICATION_URL", "http://127.0.0.1:8006")


def publish_event(event_type: str, payload: dict) -> None:
    event = {
        "type": event_type,
        "payload": payload,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        requests.post(f"{NOTIFICATION_URL}/events", json=event, timeout=2)
    except requests.RequestException:
        # La operación de negocio no debe fallar si el consumidor de eventos está caído.
        pass
