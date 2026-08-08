# HADIR | حاضر

HADIR is an Arabic- and English-first, multi-tenant attendance and workforce
management SaaS. The product uses one role-aware Flutter application, one
responsive Next.js administration portal, and a FastAPI/PostgreSQL backend.

## Repository status

The repository is being built incrementally on the `develop` branch. Stable,
tested milestones are promoted to `main`. Progress and verification evidence
are maintained in [`docs/FEATURE_MATRIX.md`](docs/FEATURE_MATRIX.md) and
[`docs/IMPLEMENTATION_PLAN.md`](docs/IMPLEMENTATION_PLAN.md).

## Planned workspace

```text
apps/
  mobile/       Flutter application for every company role
  web/          Company Admin and Platform Super Admin portal
services/
  api/          FastAPI modular monolith
docs/           Architecture, security, API, test, and operations guidance
scripts/        Lightweight Windows development helpers
.github/        Continuous integration workflows
```

## Development constraints

- Windows-native PostgreSQL 18 is the local database; Docker and SQLite are not
  development substitutes.
- Local development uses one Uvicorn worker and runs heavy checks sequentially.
- Flutter runtime checks use a physical Android device connected over USB; no
  emulator is used.
- Secrets belong only in ignored `.env` files. Committed examples contain
  placeholders.
- Package caches, virtual environments, data, and build artifacts should remain
  on drive F: where practical.

## Verification

From PowerShell at the repository root, run the complete foundation gate with:

```powershell
.\scripts\verify-foundation.ps1
```

The API, Flutter, and web checks run sequentially. After staging a logical
checkpoint, run `.\scripts\check-staged.ps1` before committing. GitHub Actions
repeats all quality gates from clean Linux runners and builds a debug APK
without starting an emulator.

## Local phone testing

Set up PostgreSQL once from a visible PowerShell window:

```powershell
.\scripts\setup-postgres.ps1
```

Then run the API on your laptop's LAN address:

```powershell
.\scripts\start-api-local.ps1
```

With a real Android phone connected by USB and on the same network, start the
Flutter app in another PowerShell window:

```powershell
.\scripts\run-mobile-device.ps1
```

The app shell calls `/api/v1/health/ready`, so a green local API status means
the phone reached FastAPI and FastAPI reached PostgreSQL. If the phone cannot
connect, check Windows Firewall for inbound access to port `8000` on the
private network.

## Documentation

- [Feature matrix](docs/FEATURE_MATRIX.md)
- [Implementation plan](docs/IMPLEMENTATION_PLAN.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Data model](docs/DATA_MODEL.md)
- [API specification](docs/API_SPEC.md)
- [Security](docs/SECURITY.md)
- [Test plan](docs/TEST_PLAN.md)
- [Deployment](docs/DEPLOYMENT.md)
- [Assumptions and risks](docs/ASSUMPTIONS_AND_RISKS.md)
- [Company administrator guide](docs/ADMIN_GUIDE.md)
- [Platform owner guide](docs/SUPER_ADMIN_GUIDE.md)
- [Database operations](docs/DATABASE_OPERATIONS.md)
- [Google Play release](docs/GOOGLE_PLAY_RELEASE.md)
- [Release checklist](docs/RELEASE_CHECKLIST.md)
- [Client-owned credentials checklist](docs/CREDENTIALS_CHECKLIST.md)
- [Privacy policy template](docs/PRIVACY_POLICY.md)
- [Support information](docs/SUPPORT.md)
- [Known limitations](docs/KNOWN_LIMITATIONS.md)
- [Future roadmap](docs/FUTURE_ROADMAP.md)
- [Final handoff](docs/FINAL_HANDOFF.md)
- [Production deployment bundle](deploy/README.md)

The authoritative product scope is recorded in
[`HADIR_CODEX_FINAL_MASTER_PLAN.md`](HADIR_CODEX_FINAL_MASTER_PLAN.md).
