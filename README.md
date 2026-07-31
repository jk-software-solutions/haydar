# HADIR | حاضر

HADIR is an Arabic- and English-first, multi-tenant attendance and workforce
management SaaS. The product uses one role-aware Flutter application, one
responsive Next.js administration portal, and a FastAPI/PostgreSQL backend.

## Repository status

The repository is being built incrementally on the `develop` branch. Stable,
tested milestones are promoted to `main`. Progress and verification evidence
are maintained in [`docs/IMPLEMENTATION_PLAN.md`](docs/IMPLEMENTATION_PLAN.md).

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

## Documentation

- [Implementation plan](docs/IMPLEMENTATION_PLAN.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Data model](docs/DATA_MODEL.md)
- [API specification](docs/API_SPEC.md)
- [Security](docs/SECURITY.md)
- [Test plan](docs/TEST_PLAN.md)
- [Deployment](docs/DEPLOYMENT.md)
- [Assumptions and risks](docs/ASSUMPTIONS_AND_RISKS.md)

The authoritative product scope is recorded in
[`HADIR_CODEX_MASTER_PROMPT.md`](HADIR_CODEX_MASTER_PROMPT.md).
