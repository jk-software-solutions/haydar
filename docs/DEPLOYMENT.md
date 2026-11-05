# Deployment

## Local Windows development

The Next.js server uses `HAYDAR_API_URL` for server-side FastAPI requests and
defaults locally to `http://127.0.0.1:8000/api/v1`. Deployment must set an
internal HTTPS API URL. Web session cookies become Secure automatically in
production and require HTTPS at the public edge.

- Repository: the current checkout resolved by `scripts/dev-env.ps1`
- Database: existing native PostgreSQL 18 on `localhost:5432`
- API: Python 3.12 virtual environment, one Uvicorn worker
- Web: Node/pnpm process started only while web work is being tested
- Mobile: Flutter process started only for a connected physical device
- Docker and Android emulators are not used.

Local scripts keep caches inside the ignored project cache directory. Start only
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

## Password-reset delivery

Password recovery requires a client-owned SMTP relay and public HTTPS reset URL. Set
`SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`,
`SMTP_USE_STARTTLS`, `PASSWORD_RESET_URL_BASE`, and `PASSWORD_RESET_TOKEN_MINUTES` in the
production secret store. Do not place these values in Git. Before release, request a reset for a
dedicated test account, open the delivered link, change the password, prove the link cannot be
reused, and prove all earlier sessions are revoked.

The same SMTP relay delivers in-app notification copies by email when a member enables the
`Email` notification preference. Delivery is retried by the scheduled maintenance job; failed
messages remain pending, while disabled or muted notification kinds are marked as intentionally
skipped. The maintenance unit runs the module from the active release so a release switch also
updates its notification-email code.

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

Generate the upload key once with `scripts/generate-android-upload-key.ps1`; both
key files are ignored and must be backed up securely. Use
`scripts/build-android-release.ps1` with the final production HTTPS API URL.
The script rejects placeholder/local URLs and builds signed APK/AAB artifacts
after analysis and tests. Follow `docs/GOOGLE_PLAY_RELEASE.md` for Play metadata,
privacy disclosures, screenshots, and physical-device acceptance.

## Backup and restore

Development backups use `pg_dump` custom format and record SHA-256 plus restore
test evidence. Production uses managed snapshots/PITR plus periodic logical
exports. A backup is not accepted until it can be listed and restored into an
isolated validation database.
