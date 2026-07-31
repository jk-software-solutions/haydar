# Deployment

## Local Windows development

- Repository: `F:\my_projects\Hadir`
- Database: existing native PostgreSQL 18 on `localhost:5432`
- API: Python 3.12 virtual environment, one Uvicorn worker
- Web: Node/pnpm process started only while web work is being tested
- Mobile: Flutter process started only for a connected physical device
- Docker and Android emulators are not used.

Local scripts set caches and temporary paths to F: where practical. Start only
the component required by the current task and stop child build/server processes
after validation.

## Database setup

First prove the existing cluster is healthy with an authenticated version query.
Do not modify, remove or relocate its current databases or data directory.
Create isolated `haydar_dev` and `haydar_test` databases plus `haydar_app` and
`haydar_migrator` roles. Store their generated passwords only in local `.env`.

`haydar_migrator` applies Alembic migrations. `haydar_app` owns no schema and
receives only runtime sequence/table permissions. Backups and migration checks
precede destructive production changes.

Run the local bootstrap from the repository root:

```powershell
.\scripts\setup-postgres.ps1
```

The script prompts only for the existing PostgreSQL administrator password,
generates the application and migration passwords, writes them to the ignored
root `.env`, and verifies role access to `haydar_dev` and `haydar_test`.

## Local phone-to-laptop testing

Start FastAPI on all local interfaces with one worker:

```powershell
.\scripts\start-api-local.ps1
```

The script prints the LAN URL, for example
`http://192.168.1.50:8000/api/v1`. Start the Flutter app on a real USB device
with the same URL:

```powershell
.\scripts\run-mobile-device.ps1
```

This passes `API_BASE_URL` through `--dart-define`. The mobile foundation shell
checks `/health/ready`, which is backed by a real `SELECT 1` database query.
No emulator is created. If the phone cannot reach the API, allow inbound
private-network access to port `8000` in Windows Firewall.

## Production target

The initial deployment uses:

- a managed PostgreSQL service with encryption, backups and point-in-time
  recovery;
- private S3-compatible object storage;
- FastAPI/Uvicorn supervised by the operating system;
- a Next.js standalone Node process supervised by the operating system;
- Nginx as TLS terminator and reverse proxy; and
- a managed DNS/domain and restricted network/security-group rules.

No Docker image or Compose dependency is required.

## Release sequence

1. Verify backups and database compatibility.
2. Build and test immutable API/web artifacts in CI.
3. Run Alembic migrations with the migration identity.
4. Start new application processes and verify live/ready endpoints.
5. Switch proxy traffic, run smoke tests and monitor errors.
6. Roll back application artifacts if needed; use documented forward migrations
   rather than automatically reversing destructive schema changes.

## CI/CD

GitHub Actions runs independent API, mobile, and web jobs; commands within each
job run sequentially. The workflow uses Python 3.12, Flutter 3.44.7, Java 21,
Node 24.14.1, and pnpm 10.33.3, then produces a seven-day debug APK artifact.
Native PostgreSQL is installed/configured on the runner when database
integration tests begin; service containers are not used. `develop` receives
checkpoint pushes. A tested milestone is promoted to `main` through a pull
request.

## Android release

Release signing values are requested at the release milestone and stored
outside Git. Build an obfuscated AAB with split debug information, test Arabic
and English on a physical Android device, then prepare Play Console metadata,
privacy disclosures, screenshots and the submission checklist.

## Backup and restore

Development backups use `pg_dump` custom format and record SHA-256 plus restore
test evidence. Production uses managed snapshots/PITR plus periodic logical
exports. A backup is not accepted until it can be listed and restored into an
isolated validation database.
