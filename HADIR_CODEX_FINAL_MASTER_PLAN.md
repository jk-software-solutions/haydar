# HADIR | حاضر
## Final Master Audit + Full Requirements + 30-Day Implementation Plan for Codex

> This file is the single source of truth for Codex. Codex must inspect the current repository first, preserve working code, verify every requirement, implement only what is missing/partial, test each critical flow, and keep the project aligned with this document.

---

# 1) Project Overview

- Product: **HADIR | حاضر**
- Type: Multi-tenant SaaS attendance and workforce-management platform
- Mobile: **one Flutter app only**
- Backend: **FastAPI**
- Database: **PostgreSQL**
- Web: **Next.js** Company Admin + Super Admin
- Notifications: Firebase Cloud Messaging + in-app notification center
- Maps: Google Maps + GPS/Geofencing
- Languages: Arabic + English with RTL/LTR
- Primary release: Android + Google Play
- Delivery target: 30 calendar days for the agreed MVP
- Advanced server-side face recognition: Phase 2 unless scope is changed explicitly
- iOS publishing: Phase 2 unless separately agreed

---

# 2) Non-Negotiable Development Constraints

The development laptop has only about 8 GB RAM.

Rules:

- **Do not use Docker.**
- **Do not use Docker Compose.**
- **Do not use Kubernetes.**
- **Do not use Android Emulator.**
- Test Flutter on a **real Android device**.
- Run heavy services/builds/tests sequentially.
- Use one Uvicorn worker locally.
- Avoid Redis/Celery unless truly necessary.
- Prefer lightweight PostgreSQL-backed scheduling/outbox for reminders and retries.
- Stop unused Node/Gradle/Java/Dart/Python/Uvicorn processes after testing.
- Do not replace PostgreSQL with SQLite.
- SQLite/Drift/Isar may only be used later for optional local cache, not as the central database.

Local development architecture:

```text
Flutter Android App
        ↓
FastAPI on development laptop
        ↓
Local PostgreSQL
```

The Flutter app must never connect directly to PostgreSQL.

For local real-device testing, FastAPI may listen on `0.0.0.0:8000` and Flutter may use the laptop LAN IP.

Production must use HTTPS.

---

# 3) Current Repository Audit — Codex Must Do This First

Before writing new code, inspect the repository and report:

- repository root
- current branch
- Git remotes
- `main` / `develop` branches
- working tree status
- Flutter app status
- FastAPI status
- Next.js status
- PostgreSQL status
- migrations
- authentication
- roles/permissions
- existing screens
- tests
- CI
- deployment setup
- documentation
- real blockers

Create/update `docs/FEATURE_MATRIX.md` with one row per requirement and one of:

- `PASS`
- `PARTIAL`
- `MISSING`
- `BLOCKED`
- `NOT_APPLICABLE`

For each module record:

```text
Module:
Status:
What already works:
What is missing:
Tests available:
Security concerns:
Next action:
```

Do not rebuild a working feature without a real reason.

---

# 4) Required Documentation

Create/update:

```text
docs/
  IMPLEMENTATION_PLAN.md
  ARCHITECTURE.md
  DATA_MODEL.md
  API_SPEC.md
  SECURITY.md
  TEST_PLAN.md
  DEPLOYMENT.md
  ASSUMPTIONS_AND_RISKS.md
  FEATURE_MATRIX.md
  RELEASE_CHECKLIST.md
  CLIENT_CREDENTIALS_CHECKLIST.md
```

---

# 5) Core Product Architecture

There is only **one mobile app**.

User experiences are role-based inside the same Flutter app:

- Company Owner
- Company Manager
- Supervisor
- HR Officer
- Employee

There is one web portal with:

- Company Admin area
- Platform Super Admin area

Do not create separate downloadable Employee and Manager apps.

---

# 6) Roles and Granular Permissions

Platform role:

- `SUPER_ADMIN`

Company roles:

- `COMPANY_OWNER`
- `COMPANY_MANAGER`
- `SUPERVISOR`
- `HR_OFFICER`
- `EMPLOYEE`

Permission actions:

- View
- Create
- Edit
- Delete
- Approve
- Reject
- Export
- Assign
- Manage

Permission domains:

- Employees
- Managers/Supervisors
- Branches
- Departments/Groups
- Shifts
- Attendance
- Manual Attendance
- Attendance Corrections
- Permission Requests
- Proof of Presence
- Geofence Exit Events
- Tasks
- Leave
- Documents
- Notifications
- Reports
- Exports
- Roles
- Subscription
- Company Settings
- Audit Logs

All authorization must be enforced on the backend, not only in the UI.

---

# 7) Manager / Supervisor Creation

A Company Owner or authorized manager must be able to:

- create Manager/Supervisor
- invite/activate/deactivate them
- assign branches
- assign employee groups
- assign shifts where needed
- configure exact permissions
- edit/revoke permissions
- limit access to assigned scope only
- view activity and audit history

This must work consistently in API, mobile where applicable, and web dashboard.

---

# 8) Authentication and Account Lifecycle

Required:

- company registration
- login by email and/or phone
- modern password hashing (Argon2id preferred)
- access token
- refresh token
- rotating/revocable sessions
- logout
- password reset
- invitation activation
- account activation/deactivation
- company suspension
- employee suspension
- trial state
- expired subscription state

Security:

- short-lived access tokens
- refresh-token revocation
- reuse detection where practical
- tokens never logged
- passwords never logged
- Flutter Secure Storage for mobile tokens
- secure HttpOnly web cookies where practical

---

# 9) Login Flow

One app only.

Recommended flow:

```text
Splash
→ Language
→ Login
→ Backend resolves company membership + role
→ Role/permission-based navigation
```

The UI may clearly explain Employee vs Manager/Supervisor access, but must not create separate apps.

---

# 10) Multi-Tenant Isolation

Every company-owned row must be tenant-scoped.

Requirements:

- `company_id` on tenant-owned records
- never trust arbitrary client-supplied tenant IDs
- derive tenant from authenticated membership/session
- repository/service tenant filters
- authorization policies
- tenant-safe background jobs
- tenant-safe exports
- tenant-safe file paths
- tenant-safe notifications
- automated cross-company access tests

PostgreSQL RLS may be added later as defense-in-depth, but application-level isolation is mandatory first.

---

# 11) Company Settings

Support:

- company name/logo
- country
- time zone
- default language
- second language
- work week
- attendance rules
- late rules
- early departure rules
- default geofence radius
- Proof of Presence settings
- ranking settings
- notification settings
- subscription status/usage
- active/suspended state

---

# 12) Branches

Each branch supports:

- name
- code
- general address
- **Saudi Short Address**
- latitude
- longitude
- geofence radius
- time zone
- working hours
- branch manager
- supervisors
- employees
- active/inactive state

Location entry:

- Google Maps picker
- manual address
- manual coordinates where needed
- Saudi Short Address field

Employee transfer between branches must preserve the employee account and maintain transfer history.

---

# 13) Departments / Groups

Support departments and teams/groups for:

- employee assignment
- manager/supervisor responsibility
- task targeting
- Proof of Presence targeting
- reporting filters

---

# 14) Employee Profile

At minimum:

- full name
- employee number
- phone
- email
- department
- job title
- direct manager
- branch
- shift
- employee status
- join date
- leave balances
- device state
- documents
- attendance summary

---

# 15) Shift Management

Support:

- multiple shifts
- name
- start/end time
- overnight shifts
- work days
- grace period
- break duration
- effective date range
- branch assignment
- employee assignment
- recurrence
- exceptions
- active/inactive state
- overlap/conflict validation

Historical attendance must keep the correct original shift context.

---

# 16) One-Device Employee Binding

Required:

- app-generated installation UUID
- server-side device record
- first activation
- one approved device per employee
- sensitive-action device validation
- unauthorized-device screen
- device-change request
- manager approval
- old-device revocation
- device history
- audit log
- future Google Play Integrity integration point

Do not rely on a single unstable hardware identifier.

---

# 17) Attendance Core

Backend is authoritative.

Check-in must validate:

- company active
- subscription active
- employee active
- employee belongs to company
- branch assignment
- shift assignment
- time window
- approved device
- no duplicate check-in
- no conflicting open attendance session
- attendance method rules
- geofence where required

Store:

- company
- employee
- branch
- shift
- check-in time
- check-out time
- coordinates
- distance from branch
- attendance method
- device
- status
- late minutes
- early-departure minutes
- worked duration
- manual flag
- approval info
- audit metadata

Statuses:

- On Time
- Late
- Absent
- Approved Leave
- Approved Permission
- Early Departure
- Unauthorized Departure
- Manual Attendance
- Pending Review
- Missing Check-Out

---

# 18) GPS / Geofencing Attendance

Mobile:

- request location permission
- handle denied/permanently denied
- handle GPS disabled
- read location
- send coordinates to backend

Backend:

- calculate distance server-side
- validate branch radius
- reject outside-area attendance
- provide clear error states

Do not trust client-calculated distance.

---

# 19) Automatic Geofence Exit / Unauthorized Leaving

This feature is mandatory and separate from Proof of Presence.

During an active shift:

1. employee has an open attendance session
2. system detects exit from allowed branch radius
3. backend checks approved permission/early departure covering that time
4. if approved: do not classify as unauthorized
5. if not approved:
   - create geofence-exit event
   - notify manager/supervisor
   - mark event for review
6. avoid false positives using configurable grace/reconfirmation
7. record time, coordinates, distance, employee, branch, shift, device, permission state
8. provide manager review UI

Android background-location behavior must respect Play policy and battery limitations. Document any OS limitations honestly.

---

# 20) QR Attendance

Required:

- server-generated branch QR token
- short expiration
- replay protection
- wrong-branch protection
- Flutter scanner
- backend validation
- approved-device validation

QR must not bypass company attendance rules.

---

# 21) Local Biometrics

Optional local confirmation using phone-supported:

- fingerprint
- device Face Unlock

This is local device authentication only, not server-side face recognition.

Advanced face recognition remains Phase 2.

---

# 22) Check-Out and Attendance Rules

Implement:

- normal check-out
- duplicate prevention
- worked hours
- late calculation
- early-departure calculation
- missing check-out
- shift-aware logic
- permission-aware logic

---

# 23) Manual Attendance / Corrections

Authorized manager/HR can create or correct attendance.

Require:

- employee
- date
- branch
- check-in/check-out where applicable
- mandatory reason
- optional attachment
- confirmation

Audit:

- actor
- old values
- new values
- reason
- timestamp
- session/IP metadata where practical

Manual records must be clearly marked.

---

# 24) Hourly Permission and Early Departure

Employee may request:

- one hour
- multiple hours
- custom time range
- early departure until shift end

Workflow:

1. submit request
2. manager notified
3. manager approves/rejects
4. optional manager comment
5. approved request changes attendance rules
6. approved early departure allows authorized checkout
7. leaving without approval becomes unauthorized according to policy

The app cannot physically prevent a person from leaving; it can enforce system authorization and record state.

---

# 25) Proof of Presence

Manager/Supervisor can send to:

- one employee
- multiple employees
- group
- branch

Options:

- response deadline
- message
- location verification
- future QR/selfie placeholder

Employee sees:

- push/in-app alert
- countdown
- respond action
- location verification

Statuses:

- Verified
- Outside Branch
- No Response
- Technical Issue
- Pending Review

Manager sees response tracking.

---

# 26) Tasks

Support:

- individual tasks
- group tasks
- branch-wide tasks

Fields:

- title
- description
- priority
- due date
- creator
- assignee(s)
- branch/group
- attachments
- status
- seen/read state

Statuses:

- New
- Viewed
- In Progress
- Completed
- Postponed
- Needs More Time
- Blocked

Employees can comment, update status, attach proof, request more time, explain blockers.

Managers can create, assign, reassign, extend deadline, review completion, comment, reopen/close where allowed.

---

# 27) Task Conversation Experience

Task detail should provide:

- chronological comments
- attachments
- read receipts
- status history
- proof of completion
- request-more-time flow
- manager responses

Do not build an unrelated full chat product.

---

# 28) Leave Management

Required:

- leave types
- annual entitlement
- request workflow
- approve/reject
- attachments
- manager comments
- adjustment audit log
- attendance integration

Employee must clearly see:

- **Total leave balance**
- **Used leave**
- **Remaining leave**

---

# 29) Employee Documents

Standard types:

- Iqama
- Passport
- Medical Insurance
- Employment Contract
- Driver License
- Vehicle Insurance
- Custom Type

Fields:

- document number
- issue date
- expiry date
- attachment
- reminder settings
- review/verification state

Statuses:

- Valid
- Expiring Soon
- Expired
- Missing
- Pending Review

---

# 30) Notification Center

Implement both push and in-app notifications.

Push via Firebase Cloud Messaging for:

- new task
- task status/deadline
- permission decision
- leave decision
- Proof of Presence
- unauthorized geofence exit to manager
- missing checkout
- shift change
- branch transfer
- device change
- document expiry
- subscription warning

In-app notification center:

- list
- read/unread
- mark one/all read
- timestamp
- type
- deep link to related screen
- history
- preferences where appropriate

Never report fake delivery success when Firebase credentials are unavailable.

---

# 31) Attendance Ranking / Motivation

Optional company setting.

Support:

- first to arrive
- second to arrive
- third to arrive
- weekly punctuality
- on-time streak

Visibility:

- manager only
- branch
- company
- disabled

Do not publicly shame late/absent employees.

---

# 32) Reports

Required reports:

- attendance
- absence
- lateness
- early departure
- unauthorized geofence exits
- worked hours
- leave
- permissions
- tasks
- expiring documents
- branch summary
- shift summary
- employee summary

Filters:

- date range
- employee
- branch
- department
- shift
- status

---

# 33) PDF / Excel Exports

Generate server-side:

- PDF
- XLSX

Requirements:

- tenant-safe
- permission-checked
- filter-aware
- secure download
- export job tracking for long operations
- requester recorded

---

# 34) Plans / Subscriptions / Coupons

Plans:

- Free Trial
- Basic
- Professional
- Enterprise

Support:

- monthly/annual periods
- trial
- start/end date
- renewal state
- manual activation
- upgrade
- suspension
- trial extension
- coupon codes
- usage counters

Plan limits:

- employee count
- branch count
- storage
- reports
- attendance methods
- tasks
- documents
- support level

Enforce plan limits on backend.

---

# 35) Payment Integration

If real payment provider is not selected:

- do not fake payments
- create `PaymentProvider` abstraction
- implement real manual/test subscription activation
- document provider integration as pending external credentials/provider decision

---

# 36) Company Admin Web Dashboard

Required sections:

- Dashboard
- Employees
- Employee Details
- Managers/Supervisors
- Branches
- Departments/Groups
- Shifts
- Attendance
- Live Attendance
- Manual Attendance
- Corrections
- Approval Center
- Proof of Presence
- Geofence Exit Review
- Tasks
- Leave
- Documents
- Notifications
- Reports
- Exports
- Roles & Permissions
- Subscription & Usage
- Company Settings
- Audit Logs

---

# 37) Super Admin Web Dashboard

Required:

- platform overview
- companies
- company details
- trials
- plans
- subscriptions
- coupons
- usage
- suspended companies
- platform audit logs
- suspicious/security activity
- Support Mode
- platform settings

Support Mode must:

- show visible banner
- log operator
- log entry/exit
- never silently impersonate users

---

# 38) Mobile Navigation

Employee suggested tabs:

- Home
- Attendance
- Tasks
- Requests
- Profile

Manager/Supervisor suggested tabs:

- Dashboard
- Team
- Attendance
- Tasks
- More

Visibility must follow permissions.

---

# 39) Required Mobile Screens

Shared:

- Splash
- Language
- Login
- Forgot Password
- Invitation Activation
- Device Activation
- Unauthorized Device
- Notifications
- Profile
- Settings
- Loading/Empty/Error/Offline states

Employee:

- Home
- Current Shift
- Check-In
- Check-Out
- GPS Verification
- QR Scanner
- Biometric Confirmation
- Attendance History
- Permission Request
- Early Departure Request
- Proof of Presence
- Tasks
- Task Detail/Conversation
- Leave Balances
- Leave Request
- Documents
- Expiry Reminders

Manager/Supervisor:

- Dashboard
- Live Team State
- Employees
- Employee Detail
- Branches
- Shifts
- Manual Attendance
- Corrections
- Approval Center
- Proof of Presence
- Unauthorized Geofence Exit Events
- Task Creation/Management
- Reports
- Exports
- Subscription Usage Summary where permitted

---

# 40) Localization

Mandatory:

- Arabic
- English
- RTL
- LTR
- translation keys, not scattered hardcoded strings
- locale-aware dates/numbers
- future third-language support without redesigning screens
- localized user-facing validation/errors

---

# 41) UI Design System — No Figma Dependency

Build reusable:

- colors
- typography
- spacing
- radius
- shadows
- buttons
- fields
- selects
- search
- cards
- status chips
- dialogs
- bottom sheets
- tables
- pagination
- empty states
- error states
- skeleton/loaders
- snackbars
- upload components
- date/time pickers

Direction:

- clean modern Saudi SaaS
- strong Arabic typography
- professional
- accessible
- minimal visual clutter
- large touch targets

---

# 42) Core Data Model Checklist

Identity / tenancy:

- users
- user_sessions
- companies
- company_memberships
- invitations
- roles
- permissions
- role_permissions
- membership_roles
- devices
- device_change_requests

Organization:

- branches
- departments
- employee_profiles
- employee_branch_history
- shifts
- shift_assignments
- shift_exceptions

Attendance:

- attendance_records
- attendance_events
- attendance_corrections
- qr_tokens
- geofence_exit_events
- permission_requests
- permission_approvals
- proof_of_presence_requests
- proof_of_presence_responses

Tasks:

- tasks
- task_assignees
- task_comments
- task_attachments
- task_status_history
- task_read_receipts

Leave / documents:

- leave_types
- leave_balances
- leave_requests
- leave_approvals
- document_types
- employee_documents
- document_reminders

Notifications / reports:

- notifications
- notification_preferences
- push_device_tokens
- export_jobs
- audit_logs

SaaS:

- plans
- plan_features
- subscriptions
- subscription_events
- coupons
- coupon_redemptions
- usage_counters

Use UUIDs unless there is a strong reason not to. Use UTC timestamps internally.

---

# 43) API Structure

Version under `/api/v1`.

Suggested groups:

```text
/auth
/companies
/memberships
/roles
/permissions
/employees
/managers
/devices
/branches
/departments
/shifts
/attendance
/attendance/manual
/attendance/corrections
/attendance/history
/geofence-events
/permission-requests
/proof-of-presence
/tasks
/leave
/documents
/notifications
/reports
/exports
/plans
/subscriptions
/coupons
/super-admin
/support-mode
/audit-logs
/health
```

Use validation, pagination, filtering, sorting, stable error codes, request IDs, and idempotency for sensitive operations.

---

# 44) Security Requirements

Mandatory:

- modern password hashing
- short-lived access tokens
- refresh-token revocation
- tenant isolation
- RBAC
- backend permission enforcement
- rate limiting
- request validation
- file type/size validation
- private file storage
- protected/signed downloads
- audit logs
- secure CORS
- HTTPS production only
- no secrets in repo
- `.env.example` placeholders only
- device revocation
- attendance idempotency
- backup/restore documentation
- secret scan before push where practical

Do not treat APK obfuscation as backend security.

---

# 45) File Storage

Development may use a private local storage abstraction.

Production should use one approved private object storage service such as:

- S3-compatible storage
- Google Cloud Storage
- equivalent private storage

Requirements:

- tenant-separated paths/keys
- MIME validation
- size limits
- access authorization
- employee documents not public by default

---

# 46) Production Hosting

Development is local.

Supported initial production architecture:

```text
Ubuntu VPS
  Nginx
  FastAPI service
  Next.js service
  PostgreSQL
  private/external object storage
  SSL
  backups
```

Alternative scalable Google Cloud architecture:

```text
Cloud Run or Compute
Cloud SQL PostgreSQL
Cloud Storage
Firebase Cloud Messaging
```

Do not lock business logic to a single vendor.

No Docker is required for this agreed workflow.

---

# 47) Client Ownership

Production resources should belong to the client/company:

- GitHub repo
- Google Play Console
- production hosting/cloud account
- domain/DNS
- PostgreSQL production instance
- storage
- Firebase
- Google Maps
- Android signing key/keystore
- payment-provider account when selected

Do not leave critical assets only in the developer's personal account.

---

# 48) Google Play Release Requirements

Before release:

- final application ID
- app name
- icon
- screenshots
- description
- privacy policy
- support contact
- Data Safety declarations
- location permission disclosure
- background location justification if used
- notification permission flow
- Android signing
- release AAB
- release notes

Store review duration is external and not part of guaranteed coding time.

---

# 49) Testing Requirements

Backend:

- unit tests
- service tests
- API integration tests
- auth/session tests
- tenant isolation tests
- permission tests
- shift and overnight tests
- attendance tests
- geofence tests
- unauthorized exit tests
- QR tests
- device-binding tests
- manual-attendance tests
- permission-request tests
- Proof of Presence tests
- task tests
- leave tests
- document tests
- notification tests
- subscription-limit tests
- export-security tests

Flutter:

- critical widget tests
- auth/session tests
- role-routing tests
- attendance-flow tests
- location permission states
- QR states
- device states
- request/approval states
- RTL smoke tests

Web:

- form validation
- route guards
- permission visibility
- tenant-aware behavior
- RTL smoke tests
- critical dashboard interactions

---

# 50) Required End-to-End Acceptance Flows

Codex must verify at least:

1. company registration
2. owner login
3. create branch
4. create shift
5. create/invite manager or supervisor
6. assign manager permissions
7. invite employee
8. employee activates one device
9. employee logs in
10. check-in inside geofence succeeds
11. check-in outside geofence fails
12. valid QR works
13. invalid/expired QR fails
14. hourly permission request submitted
15. manager approves
16. approved exit is not flagged unauthorized
17. exit without approval creates geofence event and manager alert
18. manager enters manual attendance with reason
19. audit log captures correction
20. manager sends Proof of Presence
21. employee responds from valid location
22. manager creates task
23. employee comments/attaches proof
24. employee requests more time
25. manager responds
26. employee sees total/used/remaining leave
27. employee requests leave
28. manager approves leave
29. attendance reflects leave
30. HR adds expiring document
31. expiry notification is created
32. reports filter correctly
33. PDF export works
34. XLSX export works
35. Super Admin manages plan
36. plan limits are enforced
37. coupon rules work
38. manual subscription activation works
39. company suspension/reactivation works
40. cross-company access is rejected
41. Arabic works RTL
42. English works LTR
43. Android app works on real device
44. production API works over HTTPS
45. backup/restore procedure is documented and verified

---

# 51) 30-Day Implementation Plan

Codex must map the current repository state onto this plan. Already-complete items are verified and marked complete, not rebuilt.

## Day 1 — Audit and Scope
- repository audit
- current feature verification
- feature matrix
- MVP/exclusions
- documentation baseline
- blockers/credentials list

## Day 2 — Foundation
- Git/branches
- FastAPI structure
- Flutter structure
- Next.js structure
- PostgreSQL connectivity
- `.env.example`
- lightweight local setup

## Day 3 — Database, Migrations, Localization, UI Foundation
- SQLAlchemy
- Alembic
- base models
- health endpoints
- DB readiness
- Arabic/English
- RTL/LTR
- design tokens
- routing

## Day 4 — Authentication + Companies
- users
- companies
- memberships
- company registration
- login
- Argon2id
- access/refresh tokens
- logout/session revocation
- Flutter real login

## Day 5 — Invitations + RBAC + Manager/Supervisor
- invitations
- roles
- granular permissions
- manager/supervisor creation
- scope assignment
- API/mobile/web guards

## Day 6 — Device Binding
- activation
- one-device rule
- device-change request
- approval
- revocation
- history
- audit

## Day 7 — Employees + Departments + Role Navigation
- employee profiles
- departments/groups
- employee list/details
- activation/deactivation
- role-aware navigation
- tenant-isolation tests

## Day 8 — Branches
- CRUD
- Google Maps
- Saudi Short Address
- geofence radius
- manager/supervisor assignment
- transfer history

## Day 9 — Shifts
- CRUD
- overnight
- grace period
- work days
- recurrence
- exceptions
- assignments
- conflict validation

## Day 10 — Branch / Shift UI
- manager mobile screens
- company web screens
- assignments
- transfers
- tests

## Day 11 — Attendance Check-In
- attendance schema
- check-in API
- validation
- open-session logic
- duplicate protection
- employee attendance home

## Day 12 — Check-Out + Rules
- check-out
- worked hours
- late
- early departure
- missing checkout
- history

## Day 13 — GPS / Geofence Attendance
- mobile location permission flow
- GPS
- server distance
- radius validation
- error states

## Day 14 — QR + Local Biometrics
- QR tokens
- expiry
- replay prevention
- scanner
- backend validation
- fingerprint/Face Unlock local auth

## Day 15 — Manual Attendance / Corrections
- manual attendance
- corrections
- reason
- attachment
- audit
- manager/web UI

## Day 16 — Permissions / Early Departure
- hourly/custom permission
- early departure
- approval/rejection
- comments
- attendance integration

## Day 17 — Automatic Geofence Exit + Proof of Presence
- geofence-exit events
- permission-aware suppression
- manager alert
- review UI
- Proof of Presence request/deadline/location result

## Day 18 — Tasks Core
- tasks
- assignees
- individual/group/branch targets
- statuses
- employee inbox

## Day 19 — Task Conversation / Attachments
- comments
- files/images
- read receipts
- history
- proof
- more-time request

## Day 20 — Manager Tasks + Notifications
- task board
- filters
- reassignment
- deadline extension
- completion review
- FCM task notifications
- in-app notification foundation

## Day 21 — Leave
- leave types
- total/used/remaining
- requests
- approval/rejection
- attachments
- attendance integration

## Day 22 — Documents / Expiry Alerts
- document types
- expiry status
- reminders
- attachments
- employee/manager/web UI

## Day 23 — Attendance Reports + Ranking
- attendance/absence/lateness
- early departure
- unauthorized exits
- hours
- filters
- optional ranking/privacy

## Day 24 — Other Reports + Exports
- leave
- permissions
- tasks
- documents
- PDF
- XLSX
- secure export jobs

## Day 25 — Plans / Limits / Coupons / Subscriptions
- plans/features
- employee/branch/storage/report limits
- trial
- coupons
- monthly/annual
- manual activation
- upgrade/suspension
- payment-provider adapter

## Day 26 — Super Admin
- platform dashboard
- companies
- trials
- plans
- subscriptions
- coupons
- usage
- suspend/reactivate
- support mode
- audit

## Day 27 — Localization / Notification Center / UX Completion
- full AR/EN audit
- RTL/LTR
- notification list/read state/deep links/preferences
- loading/empty/error/offline
- accessibility
- consistency

## Day 28 — Security + Comprehensive Tests
- tenant isolation
- roles
- sessions
- device binding
- attendance
- geofence exit
- QR
- permissions
- Proof of Presence
- tasks
- leave
- documents
- subscriptions
- exports
- rate limiting
- file security
- secret review
- fix critical bugs

## Day 29 — Production Deployment + UAT
- production FastAPI
- production Next.js
- production PostgreSQL
- migrations
- Nginx
- SSL
- backup
- storage
- Firebase
- Google Maps
- Android signing
- client UAT
- critical fixes

## Day 30 — Final QA + Handoff
- real Android device regression
- AR/EN
- GPS
- QR
- device binding
- attendance
- geofence exit
- permissions
- Proof of Presence
- tasks
- leave
- documents
- notifications
- reports
- subscriptions
- APK
- AAB
- Google Play package/submission
- source code
- docs
- training/guide

---

# 52) Definition of Done for Every Feature

A feature is complete only when:

1. DB/schema exists if required
2. migration exists
3. backend service logic works
4. backend authorization works
5. tenant isolation works
6. API works
7. required mobile/web UI works
8. loading state exists
9. empty state exists
10. error state exists
11. Arabic exists
12. English exists
13. validation exists
14. tests pass
15. sensitive action audit exists where required
16. docs updated
17. no secrets committed
18. code pushed to `develop`

---

# 53) Git Workflow

- active development: `develop`
- stable milestones/releases: `main`

For each logical checkpoint:

1. review diff
2. format
3. lint
4. run relevant tests
5. verify no secrets
6. update implementation plan
7. commit clearly
8. push to `develop`

Never force-push unless explicitly instructed.

---

# 54) CI Without Docker

Backend:

- Ruff
- Pytest
- type checking where configured
- native PostgreSQL-backed tests in CI

Flutter:

- `flutter analyze`
- `flutter test`

Web:

- ESLint
- TypeScript checks
- tests
- build

No Android emulator required in CI.

---

# 55) Environment Template

`.env.example` should include placeholders only:

```env
APP_ENV=
APP_NAME=HADIR
API_BASE_URL=
DATABASE_URL=
TEST_DATABASE_URL=
MIGRATION_DATABASE_URL=
JWT_SECRET=
JWT_ACCESS_TOKEN_MINUTES=
JWT_REFRESH_TOKEN_DAYS=
CORS_ORIGINS=
STORAGE_PROVIDER=
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
```

Never commit real secrets.

---

# 56) Phase 2 / Explicitly Out of Core MVP

Unless the client explicitly changes scope:

- advanced server-side face recognition
- payroll
- full offline-first attendance synchronization
- ERP/HR integrations
- WhatsApp integration
- AI features
- iOS App Store publication
- full marketing CMS
- real payment gateway before provider/account/credentials are selected
- any new feature not listed in this file

---

# 57) Final Acceptance Checklist

The project is not accepted until all applicable items pass:

- [ ] one Flutter app only
- [ ] real authentication
- [ ] company isolation
- [ ] owner/manager/supervisor/HR/employee role handling
- [ ] manager/supervisor creation and scoped permissions
- [ ] branches
- [ ] Saudi Short Address
- [ ] employee branch transfer
- [ ] departments/groups
- [ ] shifts
- [ ] overnight shifts
- [ ] one-device binding
- [ ] GPS attendance
- [ ] QR attendance
- [ ] local biometric confirmation
- [ ] check-out
- [ ] late/absence/early-departure rules
- [ ] manual attendance
- [ ] attendance corrections + audit
- [ ] hourly permission
- [ ] approved early departure
- [ ] automatic unauthorized geofence exit detection/review
- [ ] Proof of Presence
- [ ] tasks
- [ ] task comments/attachments/read state
- [ ] leave total/used/remaining
- [ ] leave approval workflow
- [ ] employee documents
- [ ] expiry reminders
- [ ] push notifications
- [ ] in-app notification center
- [ ] attendance ranking with privacy controls
- [ ] reports
- [ ] PDF export
- [ ] XLSX export
- [ ] Company Admin dashboard
- [ ] Super Admin dashboard
- [ ] plans
- [ ] trials
- [ ] coupons
- [ ] plan limits
- [ ] manual subscription activation
- [ ] Arabic
- [ ] English
- [ ] RTL/LTR
- [ ] rate limiting
- [ ] audit logs
- [ ] secure file access
- [ ] Android real-device test
- [ ] production HTTPS
- [ ] backup/restore
- [ ] APK
- [ ] AAB
- [ ] Google Play submission package
- [ ] client-owned production resources
- [ ] source code
- [ ] README
- [ ] deployment guide
- [ ] Admin guide
- [ ] Super Admin guide
- [ ] backup/restore guide
- [ ] known limitations
- [ ] future roadmap

---

# 58) Final Instruction to Codex

Read this file completely before changing code.

Then:

1. inspect the current repository
2. inspect current database schema/migrations
3. inspect Flutter
4. inspect FastAPI
5. inspect Next.js
6. update `FEATURE_MATRIX.md`
7. mark every requirement PASS/PARTIAL/MISSING/BLOCKED
8. preserve working code
9. fix the earliest incomplete dependency first
10. do not use Docker
11. do not use Android Emulator
12. do not replace PostgreSQL with SQLite
13. do not use mock business flows when a real backend flow is required
14. test critical mobile functionality on the real Android device
15. keep documentation current
16. push tested logical checkpoints to `develop`
17. after each checkpoint report:
    - what was verified
    - what was implemented
    - what tests passed
    - what remains
    - real blockers only

The goal is a real, secure, multi-tenant SaaS attendance platform matching the complete approved scope — not merely a visual prototype.
