$ErrorActionPreference = 'Stop'

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$CacheRoot = 'F:\dev-caches\haydar'

$Paths = @(
    $CacheRoot,
    (Join-Path $CacheRoot 'pub'),
    (Join-Path $CacheRoot 'pip'),
    (Join-Path $CacheRoot 'pnpm-store')
)

foreach ($Path in $Paths) {
    New-Item -ItemType Directory -Path $Path -Force | Out-Null
}

# Reuse the existing standard Gradle cache. Redirecting the wrapper distribution
# to F: caused Windows filesystem stalls during the first Android build.
Remove-Item Env:GRADLE_USER_HOME -ErrorAction SilentlyContinue
$env:PUB_CACHE = Join-Path $CacheRoot 'pub'
$env:PIP_CACHE_DIR = Join-Path $CacheRoot 'pip'
$env:PNPM_STORE_DIR = Join-Path $CacheRoot 'pnpm-store'
$env:HAYDAR_PROJECT_ROOT = $ProjectRoot

$PythonRoot = 'F:\tools\Python312'
if (Test-Path (Join-Path $PythonRoot 'python.exe')) {
    $env:Path = "$PythonRoot;$PythonRoot\Scripts;$env:Path"
}

$AndroidTools = Join-Path $env:LOCALAPPDATA 'Android\sdk\platform-tools'
if (Test-Path $AndroidTools) {
    $env:Path = "$AndroidTools;$env:Path"
}

$JavaRoot = 'C:\Program Files\Android\Android Studio\jbr'
if (Test-Path (Join-Path $JavaRoot 'bin\java.exe')) {
    $env:JAVA_HOME = $JavaRoot
    $env:Path = "$JavaRoot\bin;$env:Path"
}

Write-Host "Haydar development environment loaded from $ProjectRoot"
Write-Host "Caches: $CacheRoot"
