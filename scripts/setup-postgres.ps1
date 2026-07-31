param(
    [string]$PostgresHost = 'localhost',
    [int]$PostgresPort = 5432,
    [string]$PostgresAdminUser = 'postgres',
    [switch]$OverwriteEnvironment
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$EnvFile = Join-Path $ProjectRoot '.env'
$SetupScript = Join-Path $PSScriptRoot 'setup-postgres.sql'
$Psql = 'C:\Program Files\PostgreSQL\18\bin\psql.exe'

function New-HaydarSecret {
    $Bytes = [byte[]]::new(32)
    $Generator = [Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $Generator.GetBytes($Bytes)
    }
    finally {
        $Generator.Dispose()
    }
    return [Convert]::ToHexString($Bytes).ToLowerInvariant()
}

function ConvertTo-PlainText {
    param(
        [Parameter(Mandatory)]
        [Security.SecureString]$SecureString
    )

    $Pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureString)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($Pointer)
    }
    finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($Pointer)
    }
}

function Invoke-Psql {
    param(
        [Parameter(Mandatory)]
        [string]$Database,
        [Parameter(Mandatory)]
        [string]$User,
        [string[]]$Arguments = @()
    )

    & $Psql -X -w -h $PostgresHost -p $PostgresPort -U $User -d $Database @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "psql command failed for database '$Database' as '$User' with exit code $LASTEXITCODE."
    }
}

if (-not (Test-Path $Psql)) {
    throw 'PostgreSQL 18 psql.exe was not found at the expected native installation path.'
}

if (-not (Test-Path $SetupScript)) {
    throw "Missing setup SQL script at $SetupScript."
}

if ((Test-Path $EnvFile) -and -not $OverwriteEnvironment) {
    throw ".env already exists at $EnvFile. Re-run with -OverwriteEnvironment only if you intentionally want new local development secrets."
}

Write-Host 'HADIR PostgreSQL local setup' -ForegroundColor Cyan
Write-Host 'This preserves existing PostgreSQL data and creates/updates only haydar roles and databases.'
Write-Host 'Enter the existing PostgreSQL administrator password in this window only; do not paste it into chat.'

$AdminPasswordSecure = Read-Host "Password for PostgreSQL admin role '$PostgresAdminUser'" -AsSecureString
$AdminCredentialText = ConvertTo-PlainText $AdminPasswordSecure
$AppCredential = New-HaydarSecret
$MigratorCredential = New-HaydarSecret
$JwtSigningKey = New-HaydarSecret

$PreviousPgPassword = $env:PGPASSWORD
$PreviousAppPassword = $env:HAYDAR_APP_PASSWORD
$PreviousMigratorPassword = $env:HAYDAR_MIGRATOR_PASSWORD

try {
    $env:PGPASSWORD = $AdminCredentialText
    $env:HAYDAR_APP_PASSWORD = $AppCredential
    $env:HAYDAR_MIGRATOR_PASSWORD = $MigratorCredential

    Write-Host 'Checking PostgreSQL server version...'
    Invoke-Psql -Database 'postgres' -User $PostgresAdminUser -Arguments @('-Atc', 'SELECT version();')

    Write-Host 'Creating haydar_dev, haydar_test, haydar_app, and haydar_migrator...'
    Invoke-Psql -Database 'postgres' -User $PostgresAdminUser -Arguments @('-v', 'ON_ERROR_STOP=1', '-f', $SetupScript)

    $env:PGPASSWORD = $AppCredential
    Write-Host 'Verifying haydar_app runtime access...'
    Invoke-Psql -Database 'haydar_dev' -User 'haydar_app' -Arguments @('-Atc', 'SELECT current_user, current_database();')
    Invoke-Psql -Database 'haydar_test' -User 'haydar_app' -Arguments @('-Atc', 'SELECT current_user, current_database();')

    $env:PGPASSWORD = $MigratorCredential
    Write-Host 'Verifying haydar_migrator migration access...'
    Invoke-Psql -Database 'haydar_dev' -User 'haydar_migrator' -Arguments @('-Atc', 'CREATE TABLE IF NOT EXISTS migration_privilege_probe(id integer); DROP TABLE migration_privilege_probe; SELECT current_user, current_database();')
    Invoke-Psql -Database 'haydar_test' -User 'haydar_migrator' -Arguments @('-Atc', 'CREATE TABLE IF NOT EXISTS migration_privilege_probe(id integer); DROP TABLE migration_privilege_probe; SELECT current_user, current_database();')

    $EnvContent = @"
APP_ENV=development
APP_NAME=HADIR
API_BASE_URL=http://localhost:8000/api/v1

DATABASE_URL=postgresql+asyncpg://haydar_app:$AppCredential@$PostgresHost`:$PostgresPort/haydar_dev
TEST_DATABASE_URL=postgresql+asyncpg://haydar_app:$AppCredential@$PostgresHost`:$PostgresPort/haydar_test
MIGRATION_DATABASE_URL=postgresql+asyncpg://haydar_migrator:$MigratorCredential@$PostgresHost`:$PostgresPort/haydar_dev
POSTGRES_HOST=$PostgresHost
POSTGRES_PORT=$PostgresPort
POSTGRES_DB=haydar_dev
POSTGRES_USER=haydar_app
POSTGRES_PASSWORD=$AppCredential

JWT_SECRET=$JwtSigningKey
JWT_ACCESS_TOKEN_MINUTES=15
JWT_REFRESH_TOKEN_DAYS=30
CORS_ORIGINS=http://localhost:3000

STORAGE_PROVIDER=filesystem
STORAGE_LOCAL_ROOT=F:/my_projects/Hadir/data/uploads
STORAGE_BUCKET=
STORAGE_ENDPOINT=
STORAGE_ACCESS_KEY=
STORAGE_SECRET_KEY=

FIREBASE_PROJECT_ID=
FIREBASE_CREDENTIALS_PATH=
GOOGLE_MAPS_API_KEY=
DEFAULT_TIMEZONE=Asia/Riyadh
SUPER_ADMIN_EMAIL=
SUPER_ADMIN_PASSWORD=
"@

    [IO.File]::WriteAllText($EnvFile, $EnvContent, [Text.UTF8Encoding]::new($false))
    Write-Host "Created ignored local environment file at $EnvFile." -ForegroundColor Green
    Write-Host 'PostgreSQL local setup completed successfully.' -ForegroundColor Green
}
finally {
    $env:PGPASSWORD = $PreviousPgPassword
    $env:HAYDAR_APP_PASSWORD = $PreviousAppPassword
    $env:HAYDAR_MIGRATOR_PASSWORD = $PreviousMigratorPassword
    Remove-Variable AdminCredentialText, AppCredential, MigratorCredential, JwtSigningKey -ErrorAction SilentlyContinue
}
