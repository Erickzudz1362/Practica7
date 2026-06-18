$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root
$env:PYTHONPATH = "."
$env:NOTIFICATION_URL = "http://127.0.0.1:8006"
$env:PRODUCT_URL = "http://127.0.0.1:8002"
$env:INVENTORY_URL = "http://127.0.0.1:8003"
$env:CUSTOMER_URL = "http://127.0.0.1:8004"
$env:COMPANY_URL = "http://127.0.0.1:8001"

if (-not (Test-Path ".venv")) {
  python -m venv .venv
}

.\.venv\Scripts\python.exe -m pip install -r requirements.txt

$services = @(
  @{Name='notification'; AppDir='notification-service'; Port=8006},
  @{Name='auth'; AppDir='auth-service'; Port=8000},
  @{Name='company'; AppDir='company-service'; Port=8001},
  @{Name='product'; AppDir='product-service'; Port=8002},
  @{Name='inventory'; AppDir='inventory-service'; Port=8003},
  @{Name='customer'; AppDir='customer-service'; Port=8004},
  @{Name='sales'; AppDir='sales-service'; Port=8005}
)

$pids = @()
foreach ($svc in $services) {
  $args = @('-m','uvicorn','main:app','--app-dir',$svc.AppDir,'--host','127.0.0.1','--port', [string]$svc.Port)
  $process = Start-Process -FilePath ".\.venv\Scripts\python.exe" -ArgumentList $args -WorkingDirectory $root -WindowStyle Hidden -PassThru
  $pids += [pscustomobject]@{ Name=$svc.Name; Port=$svc.Port; Id=$process.Id }
}

$pids | ConvertTo-Json | Set-Content -Encoding UTF8 ".service-pids.json"
Write-Host "Servicios iniciados:"
$pids | Format-Table -AutoSize
Write-Host "Swagger principal: http://localhost:8000/docs"
