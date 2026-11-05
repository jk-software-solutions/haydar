$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$CacheRoot = Join-Path $ProjectRoot 'dev-caches'

if (-not (Test-Path $ProjectRoot)) {
    throw "Project path does not exist: $ProjectRoot"
}

$PubCache = Join-Path $CacheRoot 'pub'
$PipCache = Join-Path $CacheRoot 'pip'
$PnpmStore = Join-Path $CacheRoot 'pnpm-store'

$Paths = @(
    $CacheRoot,
    $PubCache,
    $PipCache,
    $PnpmStore
)

foreach ($Path in $Paths) {
    New-Item -ItemType Directory -Path $Path -Force | Out-Null
}

# Keep the normal Gradle cache under:
# C:\Users\user\.gradle
Remove-Item Env:GRADLE_USER_HOME -ErrorAction SilentlyContinue

$env:PUB_CACHE = $PubCache
$env:PIP_CACHE_DIR = $PipCache
$env:PNPM_STORE_DIR = $PnpmStore
$env:HAYDAR_PROJECT_ROOT = $ProjectRoot

# Android SDK
$AndroidSdk = Join-Path $env:LOCALAPPDATA 'Android\Sdk'
$AndroidPlatformTools = Join-Path $AndroidSdk 'platform-tools'

if (Test-Path $AndroidSdk) {
    $env:ANDROID_HOME = $AndroidSdk
    $env:ANDROID_SDK_ROOT = $AndroidSdk
}

if (Test-Path $AndroidPlatformTools) {
    $env:Path = "$AndroidPlatformTools;$env:Path"
}

# Java bundled with Android Studio
$JavaRoot = 'C:\Program Files\Android\Android Studio\jbr'
$JavaExecutable = Join-Path $JavaRoot 'bin\java.exe'

if (Test-Path $JavaExecutable) {
    $env:JAVA_HOME = $JavaRoot
    $env:Path = "$JavaRoot\bin;$env:Path"
}
else {
    Write-Warning "Java was not found at: $JavaRoot"
}

Write-Host "Haydar development environment loaded." -ForegroundColor Green
Write-Host "Project: $ProjectRoot"
Write-Host "Caches: $CacheRoot"
