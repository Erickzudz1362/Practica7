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
| Demo Service | 8007 | http://localhost:8007/docs |

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

## Flujo exacto de revisión

Para reproducir el enunciado completo:

1. Crear `OXXO Bolivia`, `Hipermaxi` e `IC Norte`.
2. Crear sucursales:
   - `OXXO Bolivia / Sucursal Prado`
   - `OXXO Bolivia / Sucursal El Alto`
   - `Hipermaxi / Sucursal 1`
   - `IC Norte / Melchor Pérez`
3. Crear producto `Leche Pil 980cc`.
4. Cargar inventario:
   - `OXXO Bolivia / Sucursal Prado`: 100 bolsas a Bs 18.50
   - `Hipermaxi / Sucursal 1`: 19 bolsas a Bs 22.20
   - `IC Norte / Melchor Pérez`: 85 bolsas
5. Registrar cliente `Juanito Pérez`.
6. Vender 2 bolsas desde `OXXO Bolivia / Sucursal Prado` a Bs 18.50.
7. Transferir 50 bolsas desde `Sucursal Prado` hacia `Sucursal El Alto`.
8. Vender 1 bolsa desde `Hipermaxi / Sucursal 1` a Bs 22.20.
9. Consultar `GET /inventory/report/consolidated/{product_id}`. Resultado esperado:
   - `Hipermaxi / Sucursal 1`: 18 bolsas
   - `IC Norte / Melchor Pérez`: 85 bolsas
   - `OXXO Bolivia / Sucursal Prado`: 48 bolsas
   - `OXXO Bolivia / Sucursal El Alto`: 50 bolsas
10. Consultar `GET /sales/report/daily`. Resultado mínimo esperado de ventas efectivo:
    - `Leche Pil 980cc`: 2 x 18.50 = 37.00
    - `Leche Pil 980cc`: 1 x 22.20 = 22.20

El script `.\scripts\demo-flow.ps1` ejecuta automáticamente ese flujo exacto.

Tambien puedes ejecutar todo desde Swagger en un solo endpoint:

1. Login en `http://localhost:8000/docs` con `admin / admin123`.
2. Copia el `access_token`.
3. Abre `http://localhost:8007/docs`.
4. Presiona `Authorize` y pega solo el token.
5. Ejecuta `POST /demo/review-flow`.

Parametro opcional:

- `official_names=false`: crea nombres con sufijo para practicar varias veces.
- `official_names=true`: usa nombres exactos como `OXXO Bolivia`, `Hipermaxi` e `IC Norte`; usalo solo con bases limpias para evitar duplicados.

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
