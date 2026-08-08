# HADIR Feature Matrix

Audited against `HADIR_CODEX_FINAL_MASTER_PLAN.md` on 2026-08-08. This file is the
release source of truth for implementation status. A feature is `PASS` only when all
applicable schema, migration, API, tenant authorization, mobile/web UI, Arabic/English
states, tests, audit, and documentation requirements are complete.

Status meanings are exact: `PASS`, `PARTIAL`, `MISSING`, `BLOCKED`, and
`NOT_APPLICABLE`.

## Audit baseline

- Branch: `develop`; current checkpoint before this audit: `36ddfd5`.
- PostgreSQL: reachable; Alembic current/head is `20260808_0012`.
- Repository shape: one Flutter app, one FastAPI service, one Next.js portal.
- Existing user changes in `apps/web/pnpm-workspace.yaml` and `scripts/dev-env.ps1`
  are outside this checkpoint and must remain untouched.
- Android build/emulator execution is intentionally excluded from this work session at
  the user's request. Real-device and signed-artifact rows remain blocked release gates.

## Product and implementation requirements

| ID | Plan requirement | Status | Existing implementation and evidence | Missing work / next action | Test evidence required | Security concern |
|---|---|---|---|---|---|---|
| R01 | Entire-repository audit and traceable matrix | PASS | This matrix covers product, platform, security, delivery, and 45 E2E flows; source, migrations, PostgreSQL, mobile, web, tests, CI, and docs were inspected. | Keep current after every checkpoint. | Review matrix against master-plan headings and acceptance list. | False completion claims are prohibited. |
| R02 | One Flutter application for all roles | PASS | `apps/mobile` is the only Flutter app; `RoleWorkspaceScreen` routes owner, manager, supervisor, HR, and employee experiences. | Keep one package. | Role-routing widget tests. | Role UI is not an authorization boundary. |
| R03 | FastAPI + PostgreSQL + SQLAlchemy + Alembic | PASS | `services/api/app`, async SQLAlchemy models, native PostgreSQL connection, and migrations through `20260808_0012`. | Keep forward-only migrations. | Alembic upgrade/current and PostgreSQL integration suite. | Never substitute SQLite for tenant/security tests. |
| R04 | Next.js Company Admin and Super Admin web portals | PARTIAL | Authenticated company page and platform page exist under `apps/web/src/app/[lang]`. | Split dense screens, complete all controls, permission-aware visibility, notification center, and missing workflows. | Route guards, forms, AR/EN RTL/LTR, critical browser flows. | Server actions must enforce API permissions, not trust hidden controls. |
| R05 | Lightweight local workflow; no required Docker/emulator | PASS | Native scripts and CI are Docker-free; test plan prohibits emulator. | Preserve constraint. | Run native checks sequentially. | None. |
| R06 | Owner, manager, supervisor, HR, employee, super admin roles | PARTIAL | Persistent roles/permissions and platform-admin allowlist exist. | Return all membership roles in sessions and complete platform role lifecycle. | Role matrix and deny tests. | Current session response exposes only `membership.role_code`. |
| R07 | Granular per-membership permissions | MISSING | Fixed role permission catalog exists in `rbac_catalog.py`. | Add membership permission grants/denials, management API/UI, audit, and effective-permission response. | Override grant/deny and cross-tenant tests. | Fixed roles cannot satisfy least privilege per manager. |
| R08 | Branch/group scope for managers and supervisors | MISSING | Branch manager field exists; operational queries are company-wide. | Add membership scopes for branch/department/group and enforce them in every scoped query/export. | In-scope success and out-of-scope indistinguishable 404 tests. | Company-wide access is over-privileged. |
| R09 | Manager/supervisor creation with role, permissions, scope | PARTIAL | Invitation flow supports manager/supervisor roles. | Extend invitation/member management with permissions and scopes; add web/mobile controls. | Invite, activate, assign, modify, revoke flows. | Owners must be the only unrestricted company actor. |
| R10 | Company registration | PASS | `/auth/register-company` creates company, owner, employee profile, RBAC membership, and trial. | Add registration UI if self-service web/mobile registration remains enabled. | Existing PostgreSQL auth test plus UI flow. | Normalize identifiers and rate-limit endpoint. |
| R11 | Email/password login and Argon2id hashing | PASS | Real token login and password hashing/verification in auth/security modules. | Keep algorithm/version migration documented. | Valid/invalid/suspended login tests. | Never log credentials. |
| R12 | Phone login support | MISSING | Employee phone is profile metadata only. | Add normalized unique phone identity and verified phone-login policy, or document client decision to disable. | Duplicate/verification/login tests. | Phone takeover and enumeration protections required. |
| R13 | Access/refresh tokens, rotation, logout, revocation | PASS | Short access tokens, hashed refresh sessions, rotation, logout revocation, and reset-triggered all-session revocation implemented. | Add refresh-token family reuse detection as defense in depth. | Auth integration tests cover rotation, reuse rejection, and reset revocation. | Refresh tokens remain secure-storage/httpOnly-cookie only. |
| R14 | Password recovery/reset | PARTIAL | Migration `20260808_0013`, non-enumerating request, hashed expiring one-time token, reset, session revocation, SMTP adapter, and web/Flutter screens are implemented. | Configure client-owned SMTP and verify real delivery; add explicit expired-token clock test. | Ruff/mypy and 5 auth tests pass, including non-enumeration, reuse rejection, password change, and session revocation. | API never returns or logs raw reset tokens; production delivery is credential-blocked. |
| R15 | Suspended/inactive company and user handling | PARTIAL | `current_session` rejects inactive user/membership/company; platform can change company status. | Add explicit localized UX and revoke active sessions on suspension. | Login/refresh/API suspension and reactivation tests. | Existing tokens must stop immediately. |
| R16 | Expired subscription handling | PARTIAL | `active_subscription` gates several writes/features. | Centralize subscription policy and apply read-only/grace behavior consistently across all paid operations. | Expired/trial/grace/upgrade matrix. | Avoid accidental write access after expiry. |
| R17 | Strict multi-tenant isolation | PARTIAL | Composite tenant FKs and tenant-scoped queries are common; cross-company tests exist. | Audit every endpoint, attachment relation, export, scope, and support-mode path; expand adversarial tests. | Per-resource cross-company read/write/export/file tests. | Missing one tenant predicate can expose customer data. |
| R18 | Company profile/settings/timezone/locale | PASS | Company model and `/companies/current` read/update with owner permission; web settings form. | Add logo file relation when branding UI is completed. | Existing settings ownership and version tests. | Logo must use protected file access. |
| R19 | Branch CRUD, address, coordinates, radius, timezone, hours | PARTIAL | Full backend CRUD and web create/archive; Saudi Short Address stored. | Add edit/details, manager mobile screens, map picker, supervisor assignment, and validation UI. | CRUD/version/tenant/UI tests. | Server remains authoritative for coordinates/radius. |
| R20 | Google Maps picker | BLOCKED | Coordinate entry and server geofence work without Maps. | Integrate map picker after client key/package/domain restrictions are provided. | Picker and coordinate persistence on real device/web. | Required credential: `GOOGLE_MAPS_API_KEY` restricted to client-owned Android app/web domains. |
| R21 | Branch manager/supervisors | PARTIAL | One `manager_membership_id` field exists. | Add multiple scoped supervisors and effective assignment UI/API. | Role eligibility and cross-tenant assignment tests. | Do not accept arbitrary membership IDs. |
| R22 | Employee branch transfers with effective history | PASS | Effective assignment API/history and overlap/current constraints implemented. | Add full mobile/web transfer/history UX. | Existing transfer/cross-tenant test plus UI flow. | History must be append-only/audited. |
| R23 | Departments and operational groups | PARTIAL | Hierarchical departments CRUD and employee department link exist. | Add explicit groups/memberships, target groups from tasks/presence, and complete UI. | Group membership/target/isolation tests. | Group targets must never expand across tenant/scope. |
| R24 | Department/group filters across modules | MISSING | Current reports/tasks/presence do not consistently filter/target groups. | Add shared scoped filtering to employees, attendance, tasks, leave, reports, exports. | Filter correctness and scope tests. | Filters must be enforced server-side. |
| R25 | Employee profile and activation/deactivation | PARTIAL | Profile fields and attendance enable flag exist; web employee editor. | Add explicit membership activation/deactivation lifecycle, manager mobile detail, document/leave/task summaries. | Status, optimistic concurrency, authorization tests. | Deactivation must revoke sessions/devices. |
| R26 | Shift CRUD, recurrence, working days, overnight, grace, break, effective dates | PASS | Shift models/API include these rules and exceptions. | Complete edit/exception UI. | Existing overnight/conflict test plus exception cases. | Server timezone calculations are authoritative. |
| R27 | Shift assignments and conflict validation | PASS | Employee/branch assignments, effective dates, and overlap validation exist. | Add complete manager UI and bulk assignment if required. | Existing assignment conflict/tenant test. | Validate every target belongs to tenant/scope. |
| R28 | One-device binding and change approval | PASS | Device, change request, one-approved-device partial index, approval/revoke audit, and Flutter gate exist. | Add attestation provider when client service selected. | Existing device integration test and real-device flow. | Installation UUID is not hardware attestation. |
| R29 | Attendance check-in validation/open-session/duplicate protection | PASS | Server resolves active branch/shift/device, enforces one open record, and records immutable events. | Add idempotency-key persistence. | Existing PostgreSQL attendance test plus concurrency test. | Client time/location are untrusted inputs. |
| R30 | GPS permission and server geofence check | PASS | Flutter foreground permission/current position; Haversine distance and radius enforced by API. | Add accuracy/staleness policy fields and tests. | In/out boundary tests and real-device GPS flow. | Reject implausible/stale coordinates. |
| R31 | Automatic geofence-exit detection while checked in | MISSING | No geofence-exit model, report endpoint, monitor, review queue, or alerts. | Add event schema/API, permission-aware suppression, consecutive sample/grace logic, foreground-safe mobile monitor, review UI, notifications, audit. | Approved-exit suppression, unauthorized alert, reconfirmation, tenant tests. | Avoid covert/background tracking; disclose collection and minimize retention. |
| R32 | QR tokens, expiry, rotation, replay prevention | PARTIAL | Tenant/branch-scoped hashed expiring tokens and scanner exist. | Add one-time or nonce consumption/replay protection and rotation/revocation UI/tests. | Valid, invalid, expired, wrong branch, replay/concurrency tests. | Current token can be reused until expiry. |
| R33 | Local biometric confirmation | PARTIAL | Flutter `local_auth` biometric-only prompt and server event flag exist. | Add capability/fallback UX, policy configuration, tests, and real-device verification. | Available/unavailable/cancel/failure widget and device tests. | Server must not treat a client boolean as biometric proof. |
| R34 | Check-out and worked/late/early/missing rules | PARTIAL | Checkout computes worked and early-departure minutes; reconciliation marks missing checkout/absence. | Integrate approved leave fully and make scheduled job evidence explicit. | Overnight, permission, missing checkout, absence, leave tests. | Reconciliation must be idempotent. |
| R35 | Manual attendance and correction with reason/attachment/audit | PARTIAL | Manual create/update, reason, version checks, attendance event and audit log exist; web create form. | Validate protected attachment ownership/reference and expose correction UI/history. | Reason, attachment, concurrency, audit, tenant tests. | Arbitrary attachment keys are currently accepted. |
| R36 | Hourly permission and approved early departure | PARTIAL | Request/review/comment/status and checkout suppression exist; employee/manager screens exist. | Add attachment validation, dedicated early-departure UX, richer date/time validation. | Approval/rejection/overlap/checkout integration tests. | Reviewer scope must be enforced after R08. |
| R37 | Proof of Presence | PARTIAL | Request/deadline/recipient/location/status/urgent in-app notification implemented; employee attendance screen can respond. | Add group targets, manager review/detail UX, FCM delivery, and robust timeout job. | Valid/outside/late/no-response/device/scope tests. | Location response must be bound to approved device. |
| R38 | Tasks: CRUD, priority, due date, targeting, statuses | PARTIAL | Task CRUD/status/history, individual assignees, employee and manager lists exist. | Add branch/group targets, filters, reassignment, completion review, and scoped manager behavior. | Lifecycle/target/reassign/filter/isolation tests. | Assignee expansion and manager scope must be server-side. |
| R39 | Task conversation, attachments, read receipts, more-time workflow | PARTIAL | Comments, optional attachment keys, assignee viewed time, status history, and more-time status exist. | Validate file relations/access, expose receipts/history, model manager response/extension explicitly, add upload UI. | Conversation/file/read/reopen/extension tests. | Arbitrary keys and broad manager reads need tightening. |
| R40 | Leave types, balances total/used/remaining | PARTIAL | Leave type/balance schema and API return allocated/used/remaining. | Display employee balances in Flutter and company web; add accrual/reset rules if configured. | Balance/year/visibility tests. | Employees may read only their balance. |
| R41 | Leave request approval, attachment, attendance integration | PARTIAL | Request/review and balance deduction exist. | Validate files, prevent overlaps, materialize/reflect leave in attendance reports/reconciliation, complete UI. | Overlap, insufficient balance, approval rollback, attendance tests. | Concurrency lock required to prevent double spend. |
| R42 | Employee documents, review, expiry reminders | PARTIAL | Document schema/API/review, upload entry point, and maintenance notification job exist. | Securely link files, add update/delete/detail UI, reminder deduplication and employee/manager screens. | File access/review/expiry/dedup/tenant tests. | Document files are sensitive personal data. |
| R43 | FCM push notifications | BLOCKED | In-app notification rows are produced; no Firebase adapter/token registry exists. | Implement real adapter boundary and push-token API now; activate delivery after credentials. | Adapter contract/failure/retry/token tests, then real-device receipt. | Required: client-owned Firebase project, Android `google-services.json`, service credentials path/project ID. |
| R44 | In-app notification center/read all/deep links/preferences | PARTIAL | List and mark-one-read endpoints exist. | Add mark-all, preferences, unread count, typed deep links, Flutter/web center, loading/error/empty states. | Read state/preference/deep-link/tenant tests. | Targets must be authorized again when opened. |
| R45 | Optional attendance ranking/privacy | PARTIAL | Company enable/visibility setting and ranking API exist. | Add full UI, anonymity/visibility semantics, department/branch/period filters. | Disabled/visibility/tie/filter tests. | Do not expose private metrics beyond configured audience. |
| R46 | Attendance/absence/lateness/early/exit/hours reports | PARTIAL | Attendance and overview endpoints calculate core metrics. | Add unauthorized-exit report after R31, employee summary, department/shift filters, and full UI. | Filter/totals/timezone/isolation tests. | Exports must apply identical authorization/scope. |
| R47 | Leave/permission/task/document reports | PARTIAL | Overview/export code covers several datasets. | Complete dedicated report responses, filters, and web presentation. | Dataset/filter/tenant tests. | Avoid formula injection and excessive PII. |
| R48 | PDF and XLSX export jobs | PARTIAL | Tenant-scoped persistent export jobs produce real PDF/XLSX and authenticated download. | Make large jobs durable/async, add expiry/cleanup, stronger spreadsheet sanitization, UI history. | Existing XLSX plus PDF/content/isolation/expiry tests. | Current binary job storage and synchronous execution limit scale. |
| R49 | Plans, monthly/annual prices, features and limits | PARTIAL | Plan/subscription models, default catalog, trial, feature and employee/branch/storage limits exist. | Add plan CRUD/edit API/UI and enforce all report/feature limits consistently. | Each limit boundary and downgrade tests. | Central policy prevents bypass. |
| R50 | Coupons and redemption rules | PARTIAL | Coupon create/list and validation exist; redemption table exists. | Integrate atomic redemption with subscription activation and plan/cycle constraints. | Expiry/max-use/single-company/concurrent redemption tests. | Prevent race-condition over-redemption. |
| R51 | Manual subscription activation/upgrade/suspend | PASS | Super Admin company update can set status and activate plan/cycle/duration with audit. | Add event history UI. | Platform authorization and lifecycle tests. | Only platform admins may act. |
| R52 | Payment-provider adapter | BLOCKED | `/billing/payment-provider` honestly reports `not_configured`. | Define provider-neutral request/webhook/idempotency interface; activate after provider/account selection. | Contract/webhook signature/replay tests once selected. | Required: client-selected provider, merchant account, API/webhook credentials. |
| R53 | Company dashboard and operational navigation | PARTIAL | Web operations dashboard and role-aware Flutter shell exist. | Complete branch/shift/report/subscription/notification screens and permission-driven navigation. | Responsive/role/RTL/browser tests. | Never infer permissions only from role labels. |
| R54 | Super Admin dashboard, companies, plans, trials, coupons, usage, support | PARTIAL | Platform allowlist, dashboard/company status/subscription/coupons/settings/support-session audit and page exist. | Add plan CRUD, usage detail, support-mode exit/banner/tenant context and richer audit UI. | Platform deny/support expiry/exit/audit tests. | Support mode must be explicit, time-limited, visible, and fully audited. |
| R55 | Arabic/English, RTL/LTR, locale persistence | PARTIAL | Flutter ARB setup and Next locale routes/dictionaries exist. | Remove inline bilingual/hardcoded strings, fix mojibake risk, persist preference, complete all feature keys. | Full navigation smoke in AR RTL and EN LTR. | Error details should not leak internals in either locale. |
| R56 | Loading, empty, error, offline, accessibility, consistency | PARTIAL | Core screens include several loading/empty/error states and Material semantics. | Complete offline handling, retry, accessibility labels/contrast/focus, and all new screens. | Widget/browser accessibility and network-failure tests. | Offline attendance must not become a mock acceptance path. |
| R57 | API versioning, validation, pagination, filtering, optimistic concurrency | PARTIAL | `/api/v1`, Pydantic validation, pagination on core lists, and version checks on several resources. | Standardize filters/pagination/version handling across every list/mutation. | 422/page bounds/version conflict tests. | Ignore client-supplied tenant IDs. |
| R58 | Idempotency for critical mutations | MISSING | Duplicate constraints exist for attendance/device state. | Add persistent idempotency keys for attendance, approvals, exports, subscriptions, and webhooks. | Same-key same-result and payload-conflict tests. | Process-local deduplication is insufficient. |
| R59 | Rate limiting | PARTIAL | API has process-local per-IP auth/general limiter; Nginx guidance exists. | Add trusted-proxy handling and distributed limiter before multi-worker scale. | 429/retry-after/auth bucket/proxy tests. | Spoofed/incorrect client IP can weaken protection. |
| R60 | Security headers, CORS, structured errors/logging | PASS | Restricted CORS, request IDs, problem details, structured logging, and security headers implemented. | Add production CSP/HSTS at Nginx/app boundary. | Header/CORS/error regression tests. | Production proxy configuration is part of the boundary. |
| R61 | Secure file storage/access/validation | PARTIAL | Tenant-scoped authenticated upload/download, MIME allowlist, size/storage limits, SHA-256, nosniff. | Introduce storage adapter, magic-byte validation/AV hook, resource-level ACL links, retention/deletion. | Malformed MIME, unauthorized relation, cross-tenant, quota tests. | PostgreSQL binary storage is not the target high-volume production design. |
| R62 | Object storage production adapter | BLOCKED | Environment placeholders and local/DB fallback are documented. | Implement S3-compatible private adapter and activate after credentials/bucket. | Upload/download/delete/presigned authorization tests. | Required: client-owned bucket, endpoint/region, access key, secret key, encryption/retention policy. |
| R63 | Secrets and production configuration | PARTIAL | `.env.example`, ignored `.env`, staged secret checker, production templates. | Add startup rejection for all unsafe production defaults and integration-specific validation. | Production config negative tests and secret scan. | Never commit `.env`, Firebase JSON, or keystore secrets. |
| R64 | Production Linux, PostgreSQL, Nginx, SSL, systemd, maintenance | PARTIAL | Deployment configs/scripts/docs exist for API/web/systemd/Nginx/maintenance. | Execute on client-owned target and capture served-release evidence. | Service cwd, health/readiness, TLS, migration and smoke tests. | Required: SSH host/user/key, domain/DNS, production DB credentials, TLS path. |
| R65 | Backup/restore | PARTIAL | PowerShell/bash backup and restore scripts plus guide exist. | Verify encrypted/off-host production backup and isolated restore on target. | Restore drill with row/schema verification. | Backup contains all tenant and identity data. |
| R66 | CI without Docker | BLOCKED | `.github/workflows/ci.yml` defines backend PostgreSQL, web, and Flutter gates. Last observed GitHub run had repository-level `startup_failure` before jobs. | Resolve GitHub Actions account/repository runner startup condition, rerun all jobs. | Green backend/web/mobile workflow. | CI secrets must be repository/environment scoped. |
| R67 | Android identity, permissions, signing configuration | PARTIAL | Final application ID/name/icon, manifest location/camera/biometric declarations, ignored signing material and release scripts exist. | Release owner supplies final production API URL and validates notification/background disclosures. | Manifest/resource/package and signing checks. | Keystore and passwords remain client-owned secrets. |
| R68 | APK and AAB | BLOCKED | Release script is ready; build is explicitly deferred by user. | Release owner runs signed build with real HTTPS API URL. | Inspect signed APK/AAB package, endpoint, icon, permissions. | Required: client-owned keystore path, alias and passwords. |
| R69 | Physical Android device regression | BLOCKED | Device run script and checklist exist; no connected USB device was verified in this session. | Connect real Android device and run full AR/EN/GPS/QR/biometric/device/notification regression. | `flutter devices`, install/run, and captured 45-flow device evidence where applicable. | Never claim physical-device pass from widget tests. |
| R70 | Google Play submission package | BLOCKED | Privacy policy, release guide, icon, and signing/build scripts exist. | Provide screenshots/listing/support/privacy URL/Data Safety declarations and upload signed AAB from client account. | Play pre-launch checks and closed-test install. | Required: client-owned Play Console access and final listing/legal decisions. |
| R71 | Client-owned production resources | BLOCKED | Ownership requirement is documented. | Transfer/verify repo, hosting, domain, DB, storage, Firebase, Maps, signing, and payment accounts. | Ownership/access checklist signed by client. | Critical assets must not remain solely in developer accounts. |
| R72 | Required project documentation set | PARTIAL | README, architecture, API, data, security, deployment, test, admin, super-admin, DB, privacy, support, limitations, roadmap, Play and handoff docs exist. | Add release checklist and credentials checklist; update every doc for later checkpoints. | Link/command/document review. | Documentation must distinguish implemented from blocked. |
| R73 | Phase-2 exclusions | NOT_APPLICABLE | Face recognition, payroll, offline-first sync, ERP/HR, WhatsApp, AI, iOS, marketing CMS and unselected real payment gateway are explicitly excluded. | Do not add without a client scope change. | N/A. | Avoid accidental scope and data expansion. |

## End-to-end acceptance flows

These are tracked separately because an implemented API fragment is not equivalent to a
verified user flow.

| Flow | Required outcome | Status | Evidence / remaining work |
|---:|---|---|---|
| 1 | Company registration | PARTIAL | API PostgreSQL test passes; end-user registration UI acceptance remains. |
| 2 | Owner login | PASS | Real API, web and Flutter session paths exist; auth integration tests pass. |
| 3 | Create branch | PARTIAL | API/web exist; browser acceptance remains. |
| 4 | Create shift | PARTIAL | API/web exist; browser acceptance remains. |
| 5 | Create/invite manager or supervisor | PARTIAL | Role invitation works; scoped permissions are missing. |
| 6 | Assign manager permissions | MISSING | Requires R07. |
| 7 | Invite employee | PARTIAL | API/web/mobile invitation works; full UI acceptance remains. |
| 8 | Employee activates one device | PARTIAL | API/Flutter flow and DB test exist; physical-device gate blocked. |
| 9 | Employee logs in | PARTIAL | API/widget coverage exists; physical-device gate blocked. |
| 10 | Check-in inside geofence succeeds | PARTIAL | API test exists; physical-device GPS gate blocked. |
| 11 | Check-in outside geofence fails | PARTIAL | Server rule exists; explicit boundary and device tests remain. |
| 12 | Valid QR works | PARTIAL | Scanner/token validation exist; real-device flow and replay fix remain. |
| 13 | Invalid/expired QR fails | PARTIAL | Validation exists; dedicated expiry tests remain. |
| 14 | Hourly permission request submitted | PARTIAL | API/Flutter flow exists; dedicated integration test remains. |
| 15 | Manager approves | PARTIAL | API/Flutter approval exists; scope enforcement remains. |
| 16 | Approved exit is not unauthorized | MISSING | Requires automatic exit event implementation. |
| 17 | Unapproved exit creates event and alert | MISSING | Requires R31. |
| 18 | Manager enters manual attendance with reason | PARTIAL | API/web exists; attachment and UI tests remain. |
| 19 | Audit captures correction | PARTIAL | Audit/event write exists; dedicated assertion remains. |
| 20 | Manager sends Proof of Presence | PARTIAL | API/web exists; group targeting and device acceptance remain. |
| 21 | Employee responds from valid location | PARTIAL | API/Flutter exists; physical-device acceptance remains. |
| 22 | Manager creates task | PARTIAL | API/web/mobile manager flow exists; target completion remains. |
| 23 | Employee comments/attaches proof | PARTIAL | Comment UI/API exists; protected upload/link validation remains. |
| 24 | Employee requests more time | PARTIAL | Status flow exists; explicit extension request model remains. |
| 25 | Manager responds | PARTIAL | Generic task status/update exists; dedicated decision UI remains. |
| 26 | Employee sees total/used/remaining leave | PARTIAL | API computes values; Flutter display is missing. |
| 27 | Employee requests leave | PARTIAL | API/Flutter exists; attachment/overlap tests remain. |
| 28 | Manager approves leave | PARTIAL | API/Flutter exists; concurrency/scope tests remain. |
| 29 | Attendance reflects leave | MISSING | Reconciliation/report integration is incomplete. |
| 30 | HR adds expiring document | PARTIAL | API/mobile upload entry exists; secure linking/UI completion remains. |
| 31 | Expiry notification is created | PARTIAL | Maintenance job exists; dedup/scheduler acceptance remains. |
| 32 | Reports filter correctly | PARTIAL | Core filters exist; department/shift/exit coverage remains. |
| 33 | PDF export works | PARTIAL | Real generator exists; explicit PDF validation test remains. |
| 34 | XLSX export works | PASS | PostgreSQL operations test validates real XLSX content/download. |
| 35 | Super Admin manages plan | MISSING | Plan listing exists; plan CRUD/edit is absent. |
| 36 | Plan limits enforced | PARTIAL | Employee/branch/storage and method gates exist; comprehensive enforcement remains. |
| 37 | Coupon rules work | PARTIAL | Validation works; atomic redemption/subscription integration remains. |
| 38 | Manual subscription activation works | PARTIAL | API/web implementation exists; dedicated platform tests remain. |
| 39 | Company suspension/reactivation works | PARTIAL | API/web implementation exists; session revocation acceptance remains. |
| 40 | Cross-company access rejected | PARTIAL | Multiple PostgreSQL tests pass; exhaustive resource matrix remains. |
| 41 | Arabic works RTL | PARTIAL | Locale direction works; untranslated inline strings and full smoke remain. |
| 42 | English works LTR | PARTIAL | Locale direction works; full smoke remains. |
| 43 | Android app works on real device | BLOCKED | User deferred build; USB device and real runtime evidence required. |
| 44 | Production API works over HTTPS | BLOCKED | Deployment assets exist; production host/domain/SSH/DB/TLS access required. |
| 45 | Backup/restore documented and verified | PARTIAL | Documented and local scripts exist; production isolated restore drill remains. |

## Exact external inputs and credentials

No fake credential-dependent integration is permitted.

| Dependency | Required input | Current status |
|---|---|---|
| Firebase/FCM | Client-owned Firebase project ID, Android `google-services.json`, server service-account credentials path, approved Android application ID/SHA restrictions | BLOCKED |
| Password-reset email | SMTP host/port, sender address, username/password or approved relay, and final public reset URL | BLOCKED |
| Google Maps | Client-owned API key restricted for the final Android application ID/signing SHA and authorized web origins | BLOCKED |
| Object storage | Client-owned private bucket, endpoint/region, access key, secret key, encryption, retention and CORS policy | BLOCKED |
| Payment | Selected Saudi-compatible provider, merchant account, API keys, webhook secret, callback URLs and commercial rules | BLOCKED |
| Production | SSH host/user/key, domain and DNS control, PostgreSQL URLs/roles, TLS provisioning access, final CORS origins | BLOCKED |
| Android release | Client-owned upload keystore, alias/passwords and final HTTPS API URL | BLOCKED by user-deferred build |
| Google Play | Client-owned Play Console access, support contact, privacy-policy URL, listing copy/screenshots and Data Safety decisions | BLOCKED |
| Real device | Connected physical Android device with USB debugging, camera, biometrics, GPS and test accounts | BLOCKED by user-deferred build |
| GitHub CI | Repository/account Actions startup condition resolved so jobs can be scheduled | BLOCKED |

## Earliest incomplete dependency order

1. Password reset lifecycle (R14), because it completes the authentication foundation.
2. Granular permissions and manager scopes (R07-R09), because all manager-facing data
   queries depend on them.
3. Operational groups and shared scope enforcement (R23-R24).
4. Idempotency and QR replay protection (R32, R58).
5. Automatic geofence-exit detection/review (R31).
6. Secure attachment relations/storage boundary (R35, R39, R41, R42, R61-R62).
7. Notifications, leave-attendance integration, reports, subscriptions, portal/mobile UX,
   localization, and comprehensive acceptance tests.
8. External deployment, physical-device, signed artifacts, and Play gates after client inputs.
