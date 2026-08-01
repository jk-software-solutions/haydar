param(
    [switch]$AllowEmpty
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Push-Location $ProjectRoot

try {
    $StagedFiles = @(git diff --cached --name-only --diff-filter=ACMR)
    if ($LASTEXITCODE -ne 0) {
        throw 'Unable to inspect staged files.'
    }

    if ($StagedFiles.Count -eq 0) {
        if ($AllowEmpty) {
            Write-Host 'No staged files to inspect.'
            return
        }

        throw 'No staged files found.'
    }

    $ForbiddenPatterns = @(
        '(^|/)\.env($|\.)',
        '(^|/)node_modules(/|$)',
        '(^|/)\.venv(/|$)',
        '(^|/)venv(/|$)',
        '(^|/)build(/|$)',
        '(^|/)\.dart_tool(/|$)',
        '(^|/)\.next(/|$)',
        '(^|/)\.gradle(/|$)',
        '(^|/)coverage(/|$)',
        '\.(apk|aab|ipa|jks|keystore|p12|pem)$',
        '(^|/)google-services\.json$',
        '(^|/)GoogleService-Info\.plist$'
    )

    $ForbiddenFiles = foreach ($File in $StagedFiles) {
        $Normalized = $File.Replace('\', '/')
        $IsExampleEnvironment = $Normalized.EndsWith('/.env.example') -or
            $Normalized -eq '.env.example'

        if (-not $IsExampleEnvironment -and
            ($ForbiddenPatterns | Where-Object { $Normalized -match $_ })) {
            $File
        }
    }

    if ($ForbiddenFiles) {
        throw "Forbidden generated, secret, or local files are staged:`n$($ForbiddenFiles -join "`n")"
    }

    $AddedLines = git diff --cached --no-ext-diff --unified=0 -- . |
        Where-Object { $_ -match '^\+(?!\+\+\+)' }
    if ($LASTEXITCODE -ne 0) {
        throw 'Unable to inspect staged content.'
    }

    $QuotedSecretPattern = '(?i)(password|secret|token|api[_-]?key|private[_-]?key)\s*[:=]\s*["''](?!<|placeholder|example|changeme|not-configured|\$\{)[^"'']{12,}["'']'
    $EnvironmentSecretPattern = '(?i)^\+\s*[A-Z0-9_]*(PASSWORD|SECRET|TOKEN|API_KEY|PRIVATE_KEY)[A-Z0-9_]*\s*=\s*(?!<|placeholder|example|changeme|not-configured|\$\{)[A-Za-z0-9_./+=:-]{12,}\s*$'
    $SuspectedSecrets = @(
        $AddedLines | Select-String -Pattern $QuotedSecretPattern
        $AddedLines | Select-String -Pattern $EnvironmentSecretPattern
    )
    if ($SuspectedSecrets.Count -gt 0) {
        throw 'Possible secret values detected in staged additions. Review the staged diff manually.'
    }

    git diff --cached --check
    if ($LASTEXITCODE -ne 0) {
        throw 'git diff --cached --check failed.'
    }

    Write-Host "Staged checkpoint is clean: $($StagedFiles.Count) file(s)."
}
finally {
    Pop-Location
}
