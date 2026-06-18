import os
from datetime import datetime

import requests
from fastapi import Depends, FastAPI, HTTPException, Request

from common.security import current_user


app = FastAPI(title="Demo Service", version="1.0.0")

AUTH_URL = os.getenv("AUTH_URL", "http://127.0.0.1:8000")
COMPANY_URL = os.getenv("COMPANY_URL", "http://127.0.0.1:8001")
PRODUCT_URL = os.getenv("PRODUCT_URL", "http://127.0.0.1:8002")
INVENTORY_URL = os.getenv("INVENTORY_URL", "http://127.0.0.1:8003")
CUSTOMER_URL = os.getenv("CUSTOMER_URL", "http://127.0.0.1:8004")
SALES_URL = os.getenv("SALES_URL", "http://127.0.0.1:8005")
NOTIFICATION_URL = os.getenv("NOTIFICATION_URL", "http://127.0.0.1:8006")


def auth_headers(request: Request):
    return {"Authorization": request.headers.get("Authorization", "")}


def post_json(url: str, body: dict, request: Request):
    response = requests.post(url, json=body, headers=auth_headers(request), timeout=10)
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()


def get_json(url: str, request: Request):
    response = requests.get(url, headers=auth_headers(request), timeout=10)
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    return response.json()


@app.get("/health")
def health():
    return {"status": "ok", "service": "demo-service"}


@app.post("/demo/review-flow", dependencies=[Depends(current_user)])
def run_review_flow(request: Request, official_names: bool = False):
    suffix = "" if official_names else f" {datetime.now().strftime('%H%M%S%f')}"
    barcode_suffix = datetime.now().strftime("%H%M%S%f")

    oxxo = post_json(
        f"{COMPANY_URL}/companies",
        {"name": f"OXXO Bolivia{suffix}", "nit": f"100001{barcode_suffix[-3:]}"},
        request,
    )
    hipermaxi = post_json(
        f"{COMPANY_URL}/companies",
        {"name": f"Hipermaxi{suffix}", "nit": f"100002{barcode_suffix[-3:]}"},
        request,
    )
    ic_norte = post_json(
        f"{COMPANY_URL}/companies",
        {"name": f"IC Norte{suffix}", "nit": f"100003{barcode_suffix[-3:]}"},
        request,
    )

    prado = post_json(
        f"{COMPANY_URL}/branches",
        {"company_id": oxxo["id"], "city_id": 1, "name": "El Prado", "address": "Av. Prado"},
        request,
    )
    alto = post_json(
        f"{COMPANY_URL}/branches",
        {"company_id": oxxo["id"], "city_id": 4, "name": "El Alto", "address": "Ceja de El Alto"},
        request,
    )
    hiper_branch = post_json(
        f"{COMPANY_URL}/branches",
        {"company_id": hipermaxi["id"], "city_id": 1, "name": "Sucursal 1", "address": "Cochabamba"},
        request,
    )
    ic_branch = post_json(
        f"{COMPANY_URL}/branches",
        {"company_id": ic_norte["id"], "city_id": 1, "name": "Melchor Pérez", "address": "Av. Melchor Pérez"},
        request,
    )

    product = post_json(
        f"{PRODUCT_URL}/products",
        {
            "name": "Leche Pil 980cc",
            "category_id": 2,
            "brand": "Pil",
            "barcode": f"LECHE-PIL-980-{barcode_suffix}",
            "base_price": 18.5,
            "status": "ACTIVE",
        },
        request,
    )

    post_json(
        f"{INVENTORY_URL}/inventory/input",
        {
            "product_id": product["id"],
            "branch_id": prado["id"],
            "quantity": 100,
            "cost": 12,
            "price": 18.5,
            "reason": "LOTE_INICIAL_OXXO_PRADO",
        },
        request,
    )
    post_json(
        f"{INVENTORY_URL}/inventory/input",
        {
            "product_id": product["id"],
            "branch_id": hiper_branch["id"],
            "quantity": 19,
            "cost": 12,
            "price": 22.2,
            "reason": "LOTE_INICIAL_HIPERMAXI",
        },
        request,
    )
    post_json(
        f"{INVENTORY_URL}/inventory/input",
        {
            "product_id": product["id"],
            "branch_id": ic_branch["id"],
            "quantity": 85,
            "cost": 12,
            "price": 18.5,
            "reason": "LOTE_INICIAL_IC_NORTE",
        },
        request,
    )

    customer = post_json(
        f"{CUSTOMER_URL}/customers",
        {"full_name": "Juanito Pérez", "document": f"777{barcode_suffix[-4:]}", "phone": "70000000"},
        request,
    )

    sale_prado = post_json(
        f"{SALES_URL}/sales",
        {
            "customer_id": customer["id"],
            "branch_id": prado["id"],
            "payment_method": "EFECTIVO",
            "items": [{"product_id": product["id"], "quantity": 2, "unit_price": 18.5}],
        },
        request,
    )

    transfer = post_json(
        f"{INVENTORY_URL}/inventory/transfer",
        {"product_id": product["id"], "from_branch_id": prado["id"], "to_branch_id": alto["id"], "quantity": 50},
        request,
    )

    sale_hipermaxi = post_json(
        f"{SALES_URL}/sales",
        {
            "customer_id": customer["id"],
            "branch_id": hiper_branch["id"],
            "payment_method": "EFECTIVO",
            "items": [{"product_id": product["id"], "quantity": 1, "unit_price": 22.2}],
        },
        request,
    )

    consolidated = get_json(f"{INVENTORY_URL}/inventory/report/consolidated/{product['id']}", request)
    daily_sales = get_json(f"{SALES_URL}/sales/report/daily", request)
    notifications = get_json(f"{NOTIFICATION_URL}/notifications", request)
    events = get_json(f"{NOTIFICATION_URL}/events", request)

    return {
        "message": "Flujo de revisión ejecutado correctamente",
        "ids": {
            "company_oxxo": oxxo["id"],
            "branch_prado": prado["id"],
            "branch_el_alto": alto["id"],
            "company_hipermaxi": hipermaxi["id"],
            "branch_hipermaxi": hiper_branch["id"],
            "company_ic_norte": ic_norte["id"],
            "branch_ic_norte": ic_branch["id"],
            "product_leche": product["id"],
            "customer_juanito": customer["id"],
        },
        "expected": {
            "oxxo_prado": 48,
            "oxxo_el_alto": 50,
            "hipermaxi_sucursal_1": 18,
            "ic_norte_melchor_perez": 85,
            "total_quantity": 201,
            "sales_total_minimum": 59.2,
        },
        "sales": {"sale_prado": sale_prado, "sale_hipermaxi": sale_hipermaxi},
        "transfer": transfer,
        "consolidated_inventory": consolidated,
        "daily_sales": daily_sales,
        "notifications_count": len(notifications),
        "events_count": len(events),
    }
