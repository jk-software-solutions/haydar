param(
    [int]$Port = 8000,
    [switch]$Reload
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
. (Join-Path $PSScriptRoot 'dev-env.ps1')

$EnvFile = Join-Path $ProjectRoot '.env'
if (-not (Test-Path $EnvFile)) {
    throw "Missing $EnvFile. Run .\scripts\setup-postgres.ps1 first."
}

$ApiRoot = Join-Path $ProjectRoot 'services\api'
$ApiPython = Join-Path $ApiRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $ApiPython)) {
    throw "API virtual environment missing at $ApiPython."
}

$LaptopIp = Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object {
        $_.IPAddress -notlike '127.*' -and
        $_.IPAddress -notlike '169.254.*' -and
        $_.PrefixOrigin -ne 'WellKnown'
    } |
    Select-Object -First 1 -ExpandProperty IPAddress

if (-not $LaptopIp) {
    throw 'Could not detect a LAN IPv4 address. Connect Wi-Fi/Ethernet and retry.'
}

Write-Host "Starting HADIR API on http://$LaptopIp`:$Port/api/v1" -ForegroundColor Cyan
Write-Host "Phone API_BASE_URL: http://$LaptopIp`:$Port/api/v1"
Write-Host 'Use one Uvicorn worker for local development.'

$Arguments = @('-m', 'uvicorn', 'app.main:app', '--host', '0.0.0.0', '--port', "$Port", '--workers', '1')
if ($Reload) {
    $Arguments += '--reload'
}

Push-Location $ApiRoot
try {
    & $ApiPython @Arguments
}
finally {
    Pop-Location
}
