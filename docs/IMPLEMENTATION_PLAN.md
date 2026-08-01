# HADIR Implementation Plan

Last updated: 2026-08-01

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
| 3-7 | Design/localization, base schema, auth, tenancy, RBAC, devices | In progress |
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
| PostgreSQL | Completed | Native PostgreSQL 18.4 verified; `haydar_dev`, `haydar_test`, `haydar_app`, and `haydar_migrator` created; ignored root `.env` created; app and migrator roles connect to dev/test without printing secrets |
| FastAPI code foundation | Completed | Ruff format/lint, strict mypy, and 3 pytest health tests pass |
| Alembic database execution | Completed | Configuration reads the root `.env`; `alembic current` and `alembic upgrade head` connect to PostgreSQL successfully |
| Flutter foundation | Completed | One app, `com.jawadsites.haydar`; analyze and 3 tests pass; debug APK built; startup shell shows an honest ready state and a real local API/database readiness probe |
| Next.js foundation | Completed | Next 16 locale routes; lint/typecheck/build pass; 8 Vitest tests pass |
| CI | Blocked | Complete workflow and local scripts pass `actionlint`/PowerShell checks; GitHub returns `startup_failure` before even a run-only probe executes |

Flutter runtime/plugin testing remains scheduled for a physical USB-connected
Android device. No emulator was created or started. The foundation completion
records source, localization, static analysis, widget tests, identifiers, and a
successful debug APK build; it does not claim physical-device verification.
The API readiness endpoint has been smoke-tested through one local Uvicorn
worker against PostgreSQL and returned `{"status":"ok","service":"haydar-api"}`.

### Auth and navigation checkpoint

The app no longer treats backend readiness as a fake login. The foundation
screen links to a real login route after `/health/ready` succeeds. The backend
now exposes real PostgreSQL-backed owner company registration, login, session,
refresh-token rotation, and logout endpoints under `/api/v1/auth`. Tokens are
stored by the mobile login client only after the API accepts credentials.

The first auth migration is `20260801_0001_identity_auth_foundation`; it creates
companies, users, company memberships, and refresh sessions. Backend auth tests
cover owner registration, login, authenticated session lookup, invalid password
rejection, and refresh-token rotation against `haydar_test` using
`haydar_migrator` for schema setup and `haydar_app` for runtime API requests.

Successful mobile login now stores the accepted tokens and immediately opens an
authenticated workspace instead of leaving the user on the login screen. The
workspace loads the real user, company, membership, and role returned by the
API; its title changes for Owner, Manager, Supervisor, HR, and Employee roles.
App restart restores the session through `/auth/session`, refreshes an expired
access token through the rotating `/auth/refresh` flow, and clears local secure
storage when refresh fails. Logout calls the real revocation endpoint and then
clears the device session. Flutter analysis and all 5 mobile tests pass; the 4
real PostgreSQL-backed auth tests also pass. Physical-device verification of the
new navigation remains required when the user restarts the current USB build.

Invitation/RBAC enforcement, device activation, employee profiles, and each
role's functional navigation destinations remain the active Days 5-7 work.

### Tenant invitation and RBAC checkpoint

Migration `20260801_0002_tenant_invitations` is applied to `haydar_dev`. It adds
tenant-owned invitations with a composite company/inviter foreign key and adds
the matching composite membership uniqueness constraint. Invitation tokens are
generated with cryptographic randomness, stored only as SHA-256 hashes, expire
after seven days, and are accepted once under a row lock.

The API now derives a required `TenantContext` from the authenticated session,
uses stable role/permission policies for membership operations, rejects
client-supplied `company_id`, scopes invitation list/detail queries to the
session company, and returns cross-company detail requests as not found. Access
JWT validation now also verifies the referenced active refresh session and
company; refresh rotation remains bound to the exact membership and company
that issued it. All 9 API tests pass, including two-company list/detail
isolation, employee permission denial, activation, and token reuse rejection.

Role/permission persistence and management UI, invitation delivery/acceptance
for an already-existing global identity, Flutter activation screens, and web
permission visibility remain in progress for the complete Day 5 outcome.

### Mobile invitation workflow checkpoint

The single Flutter application now exposes invitation management only to Owner,
Manager, and HR roles. Authorized users can load the real tenant-scoped list,
create an invitation with the employee's name/email/role, and copy the one-time
activation token from a clearly identified private-delivery dialog. Employee
and Supervisor workspaces do not show the management action, and a direct route
attempt renders permission denied without calling the invitation API.

The login screen now links to a real invitation activation form. Submitting the
token and a new password calls `/auth/invitations/activate`, stores the returned
access/refresh session in secure storage, and routes into the workspace for the
assigned role. Arabic and English strings, RTL/LTR forms, loading, empty, error,
retry, and permission-denied states are included. Flutter analysis and all 6
tests pass. Real-device verification requires restarting the current USB build.

Persistent role/permission administration, existing-identity invitation
acceptance, external email/SMS delivery, and the Next.js company UI remain the
unfinished portions of Day 5.

### Persistent RBAC checkpoint

Migration `20260801_0003_persistent_rbac` is applied to `haydar_dev`. It creates
and seeds `roles`, `permissions`, `role_permissions`, and tenant-bound
`membership_roles`, then backfills every existing membership from its original
role. New owner and invited memberships write their role assignment in the same
transaction as account creation.

Protected invitation operations now query persisted membership-role and
role-permission records using both `company_id` and `membership_id`; they no
longer trust a hard-coded role map. Ruff format/lint, strict mypy, all 9 API
tests, and Alembic head verification pass against native PostgreSQL.

Custom-role administration and the permission-aware Next.js company portal are
the remaining Day 5 implementation work.

### Secure company web portal checkpoint

The Next.js portal now has real FastAPI-backed login and logout, with access and
rotating refresh tokens stored only in server-set HttpOnly, SameSite cookies.
The Next proxy refreshes an expired access cookie through `/auth/refresh`,
replaces both rotated cookies, and clears failed sessions. No token is exposed
to Client Components or browser storage.

`/{lang}/company` validates the FastAPI session at the data-access boundary,
rejects unauthenticated users, checks API role codes, loads tenant-scoped
invitations, and repeats authorization inside the invitation Server Action.
Authorized company roles can create validated invitations and receive the
one-time token once for private delivery.

Web lint, Next type generation, strict TypeScript, 10 Vitest tests, and the
production build pass sequentially. A local production smoke test returned HTTP
200 for `/ar/login` and redirected unauthenticated `/ar/company` to login.
Authenticated browser smoke testing still requires the local owner's password
and is not claimed by this checkpoint.

Day 5 is functionally complete for built-in roles, persisted permissions,
invitation creation/activation, API enforcement, Flutter, and company web UI.
Custom roles, external delivery, and existing-global-identity invitation
acceptance remain follow-on extensions. Day 6 device binding is next.

### Device binding backend checkpoint

Migration `20260801_0004_device_binding` is applied to `haydar_dev`. It creates
tenant-bound devices, device-change requests, and immutable audit logs, plus
persisted `devices:view` and `devices:manage` grants. Composite foreign keys tie
every member, approver, reviewer, current device, requested device, and audit
actor to the same company. Partial unique indexes enforce one approved device
and one pending change request per membership.

The first installation is approved automatically. A later installation requires
a reason and remains pending until an authorized Owner, Manager, or HR reviewer
approves or rejects it. Approval locks the request/devices, flushes revocation
of the old device before approving the replacement, and records an audit event
in the same transaction. Tenant-scoped queues and employee device history are
real API endpoints. Ruff, mypy, all 10 API tests, Alembic execution, and head
verification pass against native PostgreSQL.

### Mobile device binding checkpoint

The Flutter app now creates one persistent UUID v4 installation identity in
secure storage and registers it through the real device API after an Employee
signs in. The first approved device enters the role workspace immediately. A
replacement device must submit a reason and remains on a clear pending-approval
screen until an authorized reviewer acts; it cannot enter the employee
workspace while unapproved.

Owner, Manager, and HR workspaces now expose the tenant-scoped device-change
queue with real approve and reject actions. Direct access by other roles renders
permission denied without loading the queue. Arabic and English UI strings cover
registration, replacement, pending, error, empty, and review states.

Flutter localization generation, formatting, analysis, and all 7 mobile tests
pass, including UUID shape, login navigation, employee workspace gating, and
management visibility. Day 6 is source-complete against the PostgreSQL-backed
device API. Physical USB-device validation of secure-storage persistence and a
two-device replacement flow remains required before stable-milestone promotion.

### Organization profiles backend checkpoint

Migration `20260801_0005_organization_profiles` is applied to `haydar_dev`. It
adds Arabic-first company locale, timezone, and country settings and backfills
one tenant-owned employee profile for every existing company membership. New
owner registrations and invitation activations create their profile in the same
transaction as the membership.

Real `/companies/current` and `/employees` APIs now provide tenant-scoped
settings, self-profile, searchable employee list/detail, and versioned update
flows. Company and membership identity are never accepted from write payloads;
composite constraints, session-derived scoping, permissions, row locks,
optimistic versions, and immutable audit events protect changes. Cross-tenant
reads and writes return not found.

Ruff formatting/lint, strict mypy, all 12 PostgreSQL-backed API tests, Alembic
upgrade/head verification, and a direct `haydar_app` runtime-role read of the
new table pass. Day 7 web employee management and the complete role-aware mobile
navigation remain in progress.

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
