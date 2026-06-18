$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

if (Test-Path ".service-pids.json") {
  $items = Get-Content ".service-pids.json" -Raw | ConvertFrom-Json
  foreach ($item in $items) {
    Stop-Process -Id $item.Id -Force -ErrorAction SilentlyContinue
  }
  Remove-Item ".service-pids.json" -ErrorAction SilentlyContinue
  Write-Host "Servicios detenidos."
} else {
  Write-Host "No hay servicios registrados en .service-pids.json."
}
