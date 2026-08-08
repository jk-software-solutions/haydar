[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^https://')]
    [string]$ApiBaseUrl
)

$ErrorActionPreference = 'Stop'
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$mobileRoot = Join-Path $projectRoot 'apps\mobile'
$signingProperties = Join-Path $mobileRoot 'android\key.properties'
if (-not (Test-Path -LiteralPath $signingProperties)) {
    throw 'Missing android/key.properties. Run scripts/generate-android-upload-key.ps1 first.'
}
if ($ApiBaseUrl -match 'example\.(com|invalid)' -or $ApiBaseUrl -match 'localhost|127\.0\.0\.1') {
    throw 'Supply the real production HTTPS API URL; placeholders and localhost are rejected.'
}

Push-Location $mobileRoot
try {
    flutter clean
    if ($LASTEXITCODE -ne 0) { throw 'flutter clean failed.' }
    flutter pub get
    if ($LASTEXITCODE -ne 0) { throw 'flutter pub get failed.' }
    flutter analyze
    if ($LASTEXITCODE -ne 0) { throw 'flutter analyze failed.' }
    flutter test --no-pub
    if ($LASTEXITCODE -ne 0) { throw 'flutter test failed.' }
    flutter build apk --release "--dart-define=API_BASE_URL=$ApiBaseUrl"
    if ($LASTEXITCODE -ne 0) { throw 'Release APK build failed.' }
    flutter build appbundle --release "--dart-define=API_BASE_URL=$ApiBaseUrl"
    if ($LASTEXITCODE -ne 0) { throw 'Release AAB build failed.' }

    $artifacts = @(
        (Join-Path $mobileRoot 'build\app\outputs\flutter-apk\app-release.apk'),
        (Join-Path $mobileRoot 'build\app\outputs\bundle\release\app-release.aab')
    )
    foreach ($artifact in $artifacts) {
        $item = Get-Item -LiteralPath $artifact
        $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $artifact).Hash
        Write-Host "$($item.Name) $($item.Length) bytes SHA256=$hash"
    }
}
finally {
    Pop-Location
}
