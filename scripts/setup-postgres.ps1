$ErrorActionPreference = 'Stop'

$Psql = 'C:\Program Files\PostgreSQL\18\bin\psql.exe'
if (-not (Test-Path $Psql)) {
    throw 'PostgreSQL 18 psql.exe was not found at the expected native installation path.'
}

$SetupScript = Join-Path $PSScriptRoot 'setup-postgres.sql'
& $Psql -h localhost -p 5432 -U postgres -d postgres -f $SetupScript
if ($LASTEXITCODE -ne 0) {
    throw "PostgreSQL setup failed with exit code $LASTEXITCODE. No existing database is deleted by this script."
}
