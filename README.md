# Práctica 7 - Plataforma Distribuida para Supermercados

Backend completo para **Abuelita Serafina SuperMarket Bolivia S.A.** con arquitectura de microservicios, APIs REST, Swagger, JWT, bases SQLite independientes y comunicación por eventos hacia el servicio de notificaciones.

## Microservicios

| Servicio | Puerto | Swagger |
| --- | ---: | --- |
| Authentication Service | 8000 | http://localhost:8000/docs |
| Company Service | 8001 | http://localhost:8001/docs |
| Product Service | 8002 | http://localhost:8002/docs |
| Inventory Service | 8003 | http://localhost:8003/docs |
| Customer Service | 8004 | http://localhost:8004/docs |
| Sales Service | 8005 | http://localhost:8005/docs |
| Notification Service | 8006 | http://localhost:8006/docs |

## Ejecutar con Docker

```bash
docker compose up --build
```

Usuario inicial:

```text
username: admin
password: admin123
```

Primero obtén el token en `POST http://localhost:8000/auth/login` y úsalo como `Bearer Token` en Swagger o Postman para todos los demás servicios.

## Ejecutar localmente

Instala dependencias:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Levanta cada servicio en una terminal:

```bash
$env:PYTHONPATH="."
uvicorn main:app --app-dir auth-service --port 8000
uvicorn main:app --app-dir company-service --port 8001
uvicorn main:app --app-dir product-service --port 8002
uvicorn main:app --app-dir inventory-service --port 8003
uvicorn main:app --app-dir customer-service --port 8004
uvicorn main:app --app-dir sales-service --port 8005
uvicorn main:app --app-dir notification-service --port 8006
```

O usa los scripts incluidos:

```powershell
.\scripts\run-local.ps1
.\scripts\demo-flow.ps1
.\scripts\stop-local.ps1
```

## Flujo de defensa sugerido

1. Crear compañía: `POST /companies` con `OXXO Bolivia`.
2. Crear sucursales: `POST /branches` con `Sucursal Prado` y `Sucursal El Alto`.
3. Crear categoría y producto: `Leche Pil 980cc`, precio base `18.50`.
4. Cargar inventario con `POST /inventory/input` o `POST /inventory/loadExcel`.
5. Consultar existencias con `GET /inventory/balance`.
6. Registrar cliente `Juanito Pérez`.
7. Realizar venta en `POST /sales`, que valida stock, descuenta inventario, emite comprobante, asigna puntos y crea notificación.
8. Registrar baja con `POST /inventory/output`.
9. Transferir inventario con `POST /inventory/transfer`.
10. Consultar saldo final con `GET /inventory/report/consolidated/{product_id}` y ventas del día con `GET /sales/report/daily`.

## Importación Excel

`POST /inventory/loadExcel` espera un archivo `.xlsx` con encabezados:

```text
Producto | Sucursal | Cantidad | Costo | Precio
```

`Producto` y `Sucursal` son IDs ya creados en sus servicios.

## Eventos implementados

Los servicios publican eventos HTTP hacia `notification-service`:

- `ProductCreated`, `ProductUpdated`, `ProductDeleted`
- `InventoryLoaded`, `InventoryUpdated`, `TransferCompleted`, `StockLow`
- `SaleCreated`, `SaleCancelled`, `SaleCompleted`
- `CustomerCreated`, `PointsAssigned`

El servicio de notificaciones registra todos los eventos y crea notificaciones simuladas para ventas, transferencias, puntos, promociones y stock bajo.
