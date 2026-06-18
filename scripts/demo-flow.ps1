$ErrorActionPreference = "Stop"

function PostJson($url, $headers, $json) {
  Invoke-RestMethod -Method Post -Uri $url -Headers $headers -ContentType "application/json; charset=utf-8" -Body $json
}

$login = PostJson "http://127.0.0.1:8000/auth/login" @{} '{"username":"admin","password":"admin123"}'
$headers = @{ Authorization = "Bearer $($login.access_token)" }

$suffix = "$(Get-Date -Format 'HHmmssfff')$(Get-Random -Minimum 100 -Maximum 999)"
$company = PostJson "http://127.0.0.1:8001/companies" $headers "{`"name`":`"OXXO Bolivia $suffix`",`"nit`":`"1234567`"}"
$branch1 = PostJson "http://127.0.0.1:8001/branches" $headers "{`"company_id`":$($company.id),`"city_id`":1,`"name`":`"Sucursal Prado`",`"address`":`"Av. Prado`"}"
$branch2 = PostJson "http://127.0.0.1:8001/branches" $headers "{`"company_id`":$($company.id),`"city_id`":4,`"name`":`"Sucursal El Alto`",`"address`":`"Ceja de El Alto`"}"
$product = PostJson "http://127.0.0.1:8002/products" $headers "{`"name`":`"Leche Pil 980cc`",`"category_id`":2,`"brand`":`"Pil`",`"barcode`":`"779000000$suffix`",`"base_price`":18.50,`"status`":`"ACTIVE`"}"
PostJson "http://127.0.0.1:8003/inventory/input" $headers "{`"product_id`":$($product.id),`"branch_id`":$($branch1.id),`"quantity`":100,`"cost`":12,`"price`":18.50,`"reason`":`"LOTE_INICIAL`"}" | Out-Null
$customer = PostJson "http://127.0.0.1:8004/customers" $headers '{"full_name":"Juanito P\u00e9rez","document":"7777777","phone":"70000000"}'
PostJson "http://127.0.0.1:8005/sales" $headers "{`"customer_id`":$($customer.id),`"branch_id`":$($branch1.id),`"payment_method`":`"EFECTIVO`",`"items`":[{`"product_id`":$($product.id),`"quantity`":2,`"unit_price`":18.50}]}" | Out-Null
PostJson "http://127.0.0.1:8003/inventory/transfer" $headers "{`"product_id`":$($product.id),`"from_branch_id`":$($branch1.id),`"to_branch_id`":$($branch2.id),`"quantity`":50}" | Out-Null
PostJson "http://127.0.0.1:8005/sales" $headers "{`"customer_id`":$($customer.id),`"branch_id`":$($branch2.id),`"payment_method`":`"EFECTIVO`",`"items`":[{`"product_id`":$($product.id),`"quantity`":1,`"unit_price`":22.20}]}" | Out-Null

$balance = Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8003/inventory/report/consolidated/$($product.id)" -Headers $headers
$daily = Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8005/sales/report/daily" -Headers $headers
$notifications = Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8006/notifications" -Headers $headers

[pscustomobject]@{
  company_id = $company.id
  product_id = $product.id
  customer_id = $customer.id
  consolidated_total = $balance.total_quantity
  branch_balances = ($balance.branches | ForEach-Object { "$($_.branch_id):$($_.quantity)" }) -join ", "
  daily_income = $daily.total_income
  notifications = ($notifications | Measure-Object).Count
} | ConvertTo-Json -Depth 5
