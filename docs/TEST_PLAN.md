# Test Plan

## Principles

Tests run sequentially on the 8 GB development laptop. A passing unit test does
not replace a required database, browser, export or physical-device check.
Every completion claim records the command and observed result.

## Backend

- Unit tests: policies, calculations, token handling and validators.
- Service tests: transactions, approvals, subscription limits and audit events.
- Repository tests: all CRUD paths require tenant context.
- Database tests: Alembic upgrade, constraints, duplicate prevention and
  overnight shift behavior against native PostgreSQL.
- API tests: authentication, authorization, validation, idempotency and errors.
- Isolation tests: a Company A identity cannot read, infer, update, delete,
  export or attach files to Company B records.

Foundation commands are `ruff format --check`, `ruff check`, `mypy app`, and
`pytest`. Database tests target `haydar_test`, never `haydar_dev`.

## Flutter

- Unit/state tests for session, permissions and attendance state.
- Widget tests for loading, error, unauthorized-device and role visibility.
- Arabic RTL and English LTR smoke tests.
- Integration tests for authentication, activation, GPS permission, geofence,
  QR, biometric confirmation and attendance.
- `flutter analyze`, `flutter test`, and debug/release builds run sequentially.
- Runtime and plugin verification uses a physical Android device over USB.
  Android emulators are prohibited.

## Web

- Unit/component tests for schemas, forms, route policy rendering and tables.
- Arabic RTL and English LTR smoke tests.
- Browser tests for authentication, Company Admin, Super Admin and export flows.
- Run lint, type checks, unit tests and production build sequentially.

## Required end-to-end flows

1. Register a company and create its owner membership.
2. Create a branch and shift, then invite and activate an employee.
3. Bind one physical device and reject an unauthorized device.
4. Accept an in-geofence check-in and reject an outside-geofence attempt.
5. Approve early departure and classify checkout correctly.
6. Send and answer proof of presence.
7. Assign and complete a task with a real attachment.
8. Approve leave and reflect it in attendance.
9. Export authorized PDF and XLSX reports.
10. Create a plan and manually activate a subscription.
11. Reject equivalent cross-company access at API and repository layers.

## Checkpoint gate

Before commit and push:

1. Review `git diff` and `git diff --cached`.
2. Run relevant format, lint, type and test commands.
3. Run `git diff --check` and a staged secret scan.
4. Inspect staged paths for `.env`, caches, dependencies and build output.
5. Update implementation status with exact limitations.

## Foundation acceptance

- PostgreSQL version and authenticated connectivity verified.
- Development/test databases and least-privileged roles verified.
- Alembic upgrades the test database successfully.
- Live health endpoint succeeds independently; ready health performs `SELECT 1`.
- Backend, Flutter and web static/test/build checks pass.
- GitHub Actions complete without Docker/service containers.
- No real-device claim is made until a USB device test is observed.
