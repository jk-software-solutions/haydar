[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$DatabaseUrl,
    [string]$BackupDirectory = (Join-Path (Split-Path -Parent $PSScriptRoot) 'artifacts\backups')
)

$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Force -Path $BackupDirectory | Out-Null
$timestamp = (Get-Date).ToUniversalTime().ToString('yyyyMMddTHHmmssZ')
$archive = Join-Path $BackupDirectory "hadir-$timestamp.dump"

& pg_dump --format=custom --compress=9 --no-owner --no-privileges --dbname=$DatabaseUrl --file=$archive
if ($LASTEXITCODE -ne 0) { throw "pg_dump failed with exit code $LASTEXITCODE" }
& pg_restore --list $archive | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'The backup archive could not be listed.' }
$hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $archive).Hash
Set-Content -LiteralPath "$archive.sha256" -Value "$hash  $(Split-Path -Leaf $archive)" -Encoding ASCII
Write-Host "Backup verified: $archive"
