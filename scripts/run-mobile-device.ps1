param(
    [int]$ApiPort = 8000,
    [string]$DeviceId = ''
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
. (Join-Path $PSScriptRoot 'dev-env.ps1')

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

$FlutterRoot = Join-Path $ProjectRoot 'apps\mobile'
$ApiBaseUrl = "http://$LaptopIp`:$ApiPort/api/v1"
$FlutterArguments = @('run', "--dart-define=API_BASE_URL=$ApiBaseUrl")

if ($DeviceId) {
    $FlutterArguments = @('run', '-d', $DeviceId, "--dart-define=API_BASE_URL=$ApiBaseUrl")
}

Write-Host "Running HADIR mobile against $ApiBaseUrl" -ForegroundColor Cyan
Write-Host 'Use a real USB-connected Android device. No emulator is required or started.'

Push-Location $FlutterRoot
try {
    & flutter @FlutterArguments
}
finally {
    Pop-Location
}
