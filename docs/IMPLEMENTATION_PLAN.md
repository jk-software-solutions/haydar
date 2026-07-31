# HADIR Implementation Plan

Last updated: 2026-07-31

## Status definitions

- **Not started**: no implementation work has begun.
- **In progress**: work exists but the definition of done has not been met.
- **Blocked**: a verified external or technical dependency prevents progress.
- **Completed**: implementation, formatting, linting, tests, documentation, and
  required integration evidence all pass.

## Repository and environment audit

| Item | Verified state |
| --- | --- |
| Repository root | `F:\my_projects\Hadir` |
| GitHub | Private `jawadsites/haydar`; remote `origin` |
| Branches | Stable `main`; active development `develop` |
| Initial contents | Master prompt only; no existing application code |
| Flutter/Dart | Flutter 3.44.7; Dart 3.12.2 |
| Android | SDK 36 and Java 21 available; no USB device connected |
| Python | 3.14.4 present; Python 3.12 required side-by-side |
| Web tooling | Node 24.14.1; pnpm 10.33.3 |
| Database | Native PostgreSQL 18.4 service installed on Windows |
| Machine | 7.91 GB RAM; limited C: space; ample F: space |

No Docker, Android emulator, Redis, Celery, Kubernetes, SQLite fallback, or
separate role-specific mobile application will be introduced.

## Milestones

| Days | Deliverable | Status |
| --- | --- | --- |
| 1 | Audit, private repository, architecture and planning documents | Completed |
| 2-3 | Monorepo, native database, FastAPI, Flutter, Next.js, CI foundations | In progress |
| 3-7 | Design/localization, base schema, auth, tenancy, RBAC, devices | Not started |
| 8-10 | Branches, departments, transfers, shifts, assignments | Not started |
| 11-14 | GPS/QR attendance, device checks, checkout and history | Not started |
| 15-17 | Corrections, permissions, early departure, proof of presence | Not started |
| 18-20 | Tasks, conversations, attachments, read receipts | Not started |
| 21-22 | Leave, balances, documents and expiry reminders | Not started |
| 23-24 | Reports and server-generated PDF/XLSX exports | Not started |
| 25-26 | Plans, limits, coupons, manual activation and Super Admin | Not started |
| 27-28 | Localization, accessibility, security and E2E verification | Not started |
| 29-30 | Native deployment, Android release, Play package and handoff | Not started |

## First foundation milestone

The first stable milestone contains:

1. The complete planning and operating documentation set.
2. A native PostgreSQL connection with isolated development and test databases.
3. A FastAPI service with real database readiness checks and Alembic.
4. One Flutter shell with Arabic/English directionality and verified Android ID.
5. One Next.js portal shell with Company Admin and Super Admin route groups.
6. Sequential local verification scripts and non-container GitHub Actions.

Day 2 work may continue into Day 3. A component remains **In progress** until
its checks pass; time elapsed never changes a status to **Completed**.

### Foundation checkpoint evidence

| Component | Status | Evidence / remaining work |
| --- | --- | --- |
| Python 3.12 | Completed | Python 3.12.10 installed at `F:\tools\Python312` |
| PostgreSQL | In progress | Native 18.4 service verified present; secure setup helper now creates `haydar_dev`, `haydar_test`, `haydar_app`, `haydar_migrator`, writes ignored `.env`, and verifies role access after the local admin password is entered |
| FastAPI code foundation | Completed | Ruff format/lint, strict mypy, and 3 pytest health tests pass |
| Alembic database execution | In progress | Configuration reads the root `.env`; real migration waits for isolated database setup |
| Flutter foundation | Completed | One app, `com.jawadsites.haydar`; analyze and 3 tests pass; debug APK built; startup shell shows an honest ready state and a real local API/database readiness probe |
| Next.js foundation | Completed | Next 16 locale routes; lint/typecheck/build pass; 8 Vitest tests pass |
| CI | Blocked | Complete workflow and local scripts pass `actionlint`/PowerShell checks; GitHub returns `startup_failure` before even a run-only probe executes |

Flutter runtime/plugin testing remains scheduled for a physical USB-connected
Android device. No emulator was created or started. The foundation completion
records source, localization, static analysis, widget tests, identifiers, and a
successful debug APK build; it does not claim physical-device verification.

## Checkpoint workflow

Every logical task must:

1. Review changed and staged files.
2. Format, lint, type-check, and test only the relevant component.
3. Verify that secrets and generated artifacts are not staged.
4. Update this status file with the implementation.
5. Commit with a meaningful conventional message.
6. Push to `develop` without force.

Run `./scripts/verify-foundation.ps1` for the complete local foundation gate.
During small code-only checkpoints, the explicit `-SkipMobileBuild` or
`-SkipWebBuild` switches may avoid repeating an unchanged expensive build, but
both builds remain mandatory for milestone acceptance. Run
`./scripts/check-staged.ps1` after staging and before every commit.

GitHub Actions is enabled for the private repository and permits all actions,
but runs `30611164233`, `30611427989`, and `30611512200` each ended as
`startup_failure` with no job or log. The last probe contained only a shell
`echo`, which rules out action pins and project dependencies. The complete
workflow remains committed and locally passes `actionlint` 1.7.12; GitHub's
repository/account runner-start restriction must be resolved before CI can be
marked completed.

Promotion from `develop` to `main` requires a tested milestone and green
relevant CI. Mobile milestones additionally require a physical-device check
when runtime device behavior is in scope.

## Acceptance criteria

The MVP is accepted only when the required end-to-end flows in the master
prompt work against the real backend, cross-company access is rejected, all
role visibility is permission-driven, Arabic and English behave correctly,
server-side reports export successfully, and Android release artifacts pass
physical-device regression. External services may be disabled until their
credentials are supplied, but they must never report simulated success.

## Credentials schedule

PostgreSQL administration is needed for the foundation. Email/SMS, Firebase,
Google Maps, S3-compatible storage, Android signing, domains, TLS, and
production database credentials are requested only when their integration
milestones begin. No real credential is committed or documented here.
