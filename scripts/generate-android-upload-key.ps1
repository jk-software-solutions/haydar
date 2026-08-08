[CmdletBinding()]
param(
    [string]$Alias = "hadir_upload",
    [int]$ValidityDays = 10000
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$androidRoot = Join-Path $projectRoot "apps\mobile\android"
$releaseDirectory = Join-Path $androidRoot "release"
$keystorePath = Join-Path $releaseDirectory "hadir-upload.jks"
$propertiesPath = Join-Path $androidRoot "key.properties"

if ((Test-Path -LiteralPath $keystorePath) -or (Test-Path -LiteralPath $propertiesPath)) {
    throw "Android signing material already exists. Move it to secure backup before rotating it."
}

$keytool = Get-Command keytool -ErrorAction SilentlyContinue
if ($null -eq $keytool) {
    $javaHome = $env:JAVA_HOME
    if ([string]::IsNullOrWhiteSpace($javaHome)) {
        $androidStudioJava = "C:\Program Files\Android\Android Studio\jbr"
        if (Test-Path -LiteralPath (Join-Path $androidStudioJava "bin\keytool.exe")) {
            $javaHome = $androidStudioJava
        } else {
            throw "keytool was not found. Set JAVA_HOME to a JDK 17 installation."
        }
    }
    $keytoolPath = Join-Path $javaHome "bin\keytool.exe"
    if (-not (Test-Path -LiteralPath $keytoolPath)) {
        throw "keytool.exe was not found under JAVA_HOME."
    }
} else {
    $keytoolPath = $keytool.Source
}

New-Item -ItemType Directory -Force -Path $releaseDirectory | Out-Null
$random = [System.Security.Cryptography.RandomNumberGenerator]::Create()
$bytes = New-Object byte[] 36
$random.GetBytes($bytes)
$random.Dispose()
$password = [Convert]::ToBase64String($bytes).Replace("/", "A").Replace("+", "B")

& $keytoolPath -genkeypair -v `
    -keystore $keystorePath `
    -storepass $password `
    -keypass $password `
    -alias $Alias `
    -keyalg RSA `
    -keysize 2048 `
    -validity $ValidityDays `
    -dname "CN=HADIR Upload, OU=Mobile, O=Jawad Sites, C=SA"

if ($LASTEXITCODE -ne 0) {
    if (Test-Path -LiteralPath $keystorePath) {
        Remove-Item -LiteralPath $keystorePath -Force
    }
    throw "keytool failed with exit code $LASTEXITCODE."
}

$properties = @(
    "storePassword=$password"
    "keyPassword=$password"
    "keyAlias=$Alias"
    "storeFile=release/hadir-upload.jks"
)
$properties | Set-Content -LiteralPath $propertiesPath -Encoding ASCII

Write-Host "Created Android upload key and local Gradle signing configuration."
Write-Host "Back up these two ignored files securely before publishing:"
Write-Host "  $keystorePath"
Write-Host "  $propertiesPath"
