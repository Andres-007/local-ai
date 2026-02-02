# fix_mongodb_dns.ps1
# Añade entradas al archivo hosts para resolver el cluster MongoDB Atlas
# cuando hay problemas de DNS (timeout). Esto permite que Python conecte
# sin depender de la resolución DNS de red.
#
# EJECUTAR COMO ADMINISTRADOR: Click derecho -> "Ejecutar como administrador"
# O desde PowerShell (admin): .\fix_mongodb_dns.ps1

$hostsPath = "$env:SystemRoot\System32\drivers\etc\hosts"
$marker = "# MongoDB Atlas - cluster dataforai (fix DNS)"
$entries = @"
$marker
13.64.49.36 ac-ncgdft4-shard-00-00.iqsajt7.mongodb.net
13.91.99.217 ac-ncgdft4-shard-00-01.iqsajt7.mongodb.net
13.64.244.130 ac-ncgdft4-shard-00-02.iqsajt7.mongodb.net
"@

# Comprobar si ya existen
$content = Get-Content $hostsPath -Raw
if ($content -match [regex]::Escape($marker)) {
    Write-Host "Las entradas de MongoDB Atlas ya existen en hosts." -ForegroundColor Yellow
    exit 0
}

# Añadir entradas
Add-Content -Path $hostsPath -Value $entries -Encoding UTF8
Write-Host "Entradas añadidas correctamente a $hostsPath" -ForegroundColor Green
Write-Host "Reinicia la aplicacion (python app.py) para probar la conexion." -ForegroundColor Cyan
