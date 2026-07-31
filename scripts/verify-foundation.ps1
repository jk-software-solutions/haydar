param(
    [switch]$SkipMobileBuild,
    [switch]$SkipWebBuild
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
. (Join-Path $PSScriptRoot 'dev-env.ps1')

function Invoke-CheckedCommand {
    param(
        [Parameter(Mandatory)]
        [string]$Label,
        [Parameter(Mandatory)]
        [string]$Command,
        [string[]]$Arguments = @()
    )

    Write-Host "`n==> $Label" -ForegroundColor Cyan
    & $Command @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Label failed with exit code $LASTEXITCODE."
    }
}

try {
    $ApiRoot = Join-Path $ProjectRoot 'services\api'
    $ApiPython = Join-Path $ApiRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path $ApiPython)) {
        throw "API virtual environment missing at $ApiPython."
    }

    Push-Location $ApiRoot
    try {
        Invoke-CheckedCommand 'API formatting' $ApiPython @('-m', 'ruff', 'format', '--check', '.')
        Invoke-CheckedCommand 'API lint' $ApiPython @('-m', 'ruff', 'check', '.')
        Invoke-CheckedCommand 'API type-check' $ApiPython @('-m', 'mypy', 'app')
        Invoke-CheckedCommand 'API tests' $ApiPython @('-m', 'pytest')
    }
    finally {
        Pop-Location
    }

    $MobileRoot = Join-Path $ProjectRoot 'apps\mobile'
    Push-Location $MobileRoot
    try {
        Invoke-CheckedCommand 'Flutter dependencies' 'flutter' @('pub', 'get')
        Invoke-CheckedCommand 'Flutter localization generation' 'flutter' @('gen-l10n')
        Invoke-CheckedCommand 'Flutter analysis' 'flutter' @('analyze')
        Invoke-CheckedCommand 'Flutter tests' 'flutter' @('test')
        if (-not $SkipMobileBuild) {
            Invoke-CheckedCommand 'Flutter debug APK build' 'flutter' @('build', 'apk', '--debug')
        }
    }
    finally {
        Pop-Location
    }

    $WebRoot = Join-Path $ProjectRoot 'apps\web'
    Push-Location $WebRoot
    try {
        Invoke-CheckedCommand 'Web dependency lock verification' 'pnpm' @('install', '--frozen-lockfile')
        Invoke-CheckedCommand 'Web lint' 'pnpm' @('lint')
        Invoke-CheckedCommand 'Web type-check' 'pnpm' @('typecheck')
        Invoke-CheckedCommand 'Web tests' 'pnpm' @('test')
        if (-not $SkipWebBuild) {
            $PreviousNodeOptions = $env:NODE_OPTIONS
            try {
                $env:NODE_OPTIONS = '--max-old-space-size=1536'
                $env:NEXT_TELEMETRY_DISABLED = '1'
                Invoke-CheckedCommand 'Web production build' 'pnpm' @('build')
            }
            finally {
                $env:NODE_OPTIONS = $PreviousNodeOptions
            }
        }
    }
    finally {
        Pop-Location
    }

    Write-Host "`nFoundation verification passed." -ForegroundColor Green
}
finally {
    & (Join-Path $PSScriptRoot 'stop-dev-processes.ps1')
}
