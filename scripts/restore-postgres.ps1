[CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'High')]
param(
    [Parameter(Mandatory = $true)]
    [string]$Archive,
    [Parameter(Mandatory = $true)]
    [string]$ValidationDatabaseUrl
)

$ErrorActionPreference = 'Stop'
$resolvedArchive = (Resolve-Path -LiteralPath $Archive).Path
& pg_restore --list $resolvedArchive | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'The archive is invalid or unreadable.' }

if ($PSCmdlet.ShouldProcess($ValidationDatabaseUrl, "Restore $resolvedArchive")) {
    & pg_restore --exit-on-error --clean --if-exists --no-owner --no-privileges `
        --dbname=$ValidationDatabaseUrl $resolvedArchive
    if ($LASTEXITCODE -ne 0) { throw "pg_restore failed with exit code $LASTEXITCODE" }
    Write-Host 'Restore completed into the explicitly selected validation database.'
}
