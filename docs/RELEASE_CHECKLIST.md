# HADIR Release Checklist

Use this checklist for every candidate release. A checked source-code gate does not substitute for
a blocked client-owned infrastructure or physical-device gate.

## Source and database

- [ ] Confirm the intended branch, commit SHA, clean release scope, and excluded local-only files.
- [ ] Run secret scanning and confirm `.env`, Firebase JSON, keystores, exports, uploads, and backups
  are not tracked.
- [ ] Run Ruff formatting/lint, strict mypy, and the full PostgreSQL pytest suite.
- [ ] Run `alembic upgrade head`, `alembic current`, and confirm the expected head (`20260808_0022`
  for this checkpoint).
- [ ] Run Next.js lint, type generation/typecheck, and Vitest with `CI=true`.
- [ ] Run Flutter formatting, analysis, localization generation, and widget tests. Do not claim an
  Android artifact or device pass from these checks.

## Security and tenant acceptance

- [ ] Verify suspended companies and inactive memberships lose sessions immediately.
- [ ] Verify cross-company resource IDs return an indistinguishable 404/deny result.
- [ ] Verify uploaded files remain private, linked-resource authorization is enforced, and response
  headers prevent caching/content sniffing.
- [ ] Verify attendance idempotency, QR replay/revoke/rotation, approval replay, export replay, and
  subscription/coupon replay behavior.
- [ ] Verify support mode is visible, time-limited, administrator-bound, exited, and audited.
- [ ] Review production CORS, trusted proxy, TLS/HSTS/CSP, rate limiting, log redaction, storage
  encryption/retention, and backup access.

## Client-owned and served-release gates

- [ ] Complete every applicable item in `CREDENTIALS_CHECKLIST.md`; leave unavailable items marked
  `BLOCKED`, never replaced with fake credentials.
- [ ] Back up PostgreSQL, perform the migration with the migrator identity, start API/web services,
  and verify health/readiness through the public HTTPS origin.
- [ ] Verify the deployed release directory and process working directories point to the intended
  commit, then run authenticated smoke flows against the served application.
- [ ] Perform an isolated restore drill and record schema plus representative tenant row checks.
- [ ] On a physical Android device, validate Arabic/English, RTL/LTR, login, device binding, GPS,
  QR, biometrics, foreground geofence monitoring, notification deep links, and process-death limits.
- [ ] Only after signing inputs exist, create and inspect the APK/AAB with the final HTTPS API URL.
- [ ] Record release owner, commit, migration head, timestamps, evidence links, blocked gates, and
  rollback/forward-fix decision.
