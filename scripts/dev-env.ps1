$ErrorActionPreference = 'Stop'

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$CacheRoot = 'F:\dev-caches\haydar'

$Paths = @(
    $CacheRoot,
    (Join-Path $CacheRoot 'gradle'),
    (Join-Path $CacheRoot 'pub'),
    (Join-Path $CacheRoot 'pip'),
    (Join-Path $CacheRoot 'pnpm-store'),
    (Join-Path $CacheRoot 'temp')
)

foreach ($Path in $Paths) {
    New-Item -ItemType Directory -Path $Path -Force | Out-Null
}

$env:GRADLE_USER_HOME = Join-Path $CacheRoot 'gradle'
$env:PUB_CACHE = Join-Path $CacheRoot 'pub'
$env:PIP_CACHE_DIR = Join-Path $CacheRoot 'pip'
$env:PNPM_STORE_DIR = Join-Path $CacheRoot 'pnpm-store'
$env:TEMP = Join-Path $CacheRoot 'temp'
$env:TMP = Join-Path $CacheRoot 'temp'
$env:HAYDAR_PROJECT_ROOT = $ProjectRoot

$PythonRoot = 'F:\tools\Python312'
if (Test-Path (Join-Path $PythonRoot 'python.exe')) {
    $env:Path = "$PythonRoot;$PythonRoot\Scripts;$env:Path"
}

$AndroidTools = Join-Path $env:LOCALAPPDATA 'Android\sdk\platform-tools'
if (Test-Path $AndroidTools) {
    $env:Path = "$AndroidTools;$env:Path"
}

Write-Host "Haydar development environment loaded from $ProjectRoot"
Write-Host "Caches: $CacheRoot"
