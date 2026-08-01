# Data Model

## Conventions

- PostgreSQL UUID primary keys use server-generated UUIDs.
- Timestamps are timezone-aware UTC values: `created_at`, `updated_at`, and
  selective `deleted_at`.
- Company-owned tables include a required indexed `company_id`.
- Concurrent approval and correction aggregates include an integer `version`.
- Monetary values use integer minor units plus ISO currency codes.
- Attendance events, corrections, audit logs, and subscription events are
  append-only. Reversal or correction creates a new event.
- Composite constraints include `company_id` to prevent cross-company
  relationships even when application code is incorrect.

## Identity and tenancy

- `users`: global identity, normalized email/phone, password hash, activation
  status and locale.
- `user_sessions`: refresh-session hash/JTI, device, expiry, revocation and
  reuse-family metadata.
- `companies`: tenant identity, locale, timezone, subscription state and
  lifecycle status.
- `company_memberships`: user/company relationship and employment state.
- `roles`, `permissions`, `role_permissions`, `membership_roles`: granular
  domain/action authorization. System role codes are stable; custom company
  roles are tenant-owned.
- `invitations`: hashed token/code, target contact, company, intended roles,
  expiry, use and revocation metadata.

Migrations currently implement the five built-in company roles, persisted
domain/action permission mappings, composite tenant-bound membership roles, and
hashed one-time invitations. Custom tenant roles extend these tables later
rather than introducing a parallel authorization system.
- `devices`: installation identity, public key, approval/revocation state and
  last-seen metadata.
- `device_change_requests`: old/new devices, reason, workflow and decision.

## Organization

- `branches`: code, names, addresses, coordinates, geofence, timezone, hours,
  manager and active state.
- `departments`: tenant-scoped hierarchy and active state.
- `employee_profiles`: membership employment details and department.
- `employee_branch_history`: effective-dated assignment/transfer history.
- `shifts`: local start/end, overnight flag, workdays, grace, break and
  effective range.
- `shift_assignments`: effective branch/employee assignment.
- `shift_exceptions`: dated overrides, holidays and one-off schedules.

Assignments and references use `(company_id, referenced_id)` constraints.
Overlap checks combine database exclusions where practical with service-level
validation and transaction locking.

Migration `20260801_0005` implements company locale/timezone/country settings
and one employee profile per company membership. Profiles include tenant-local
display name, employee number, contact and job metadata, employment type, hire
date, preferred locale, attendance eligibility, optimistic version, and UTC
timestamps. Composite membership foreign keys and tenant-local employee-number
uniqueness prevent cross-company references and collisions.

Migration `20260801_0006` implements tenant-owned departments, branches, and
effective-dated employee branch assignments. Departments support tenant-bound
parents. Branches store codes, Saudi short/full addresses, server-authoritative
coordinates and geofence radius, timezone, working hours, optional same-tenant
manager, active state, and optimistic version. Assignment rows bind employee,
branch, and actor through composite company foreign keys; a partial unique index
permits only one open assignment per employee while retaining immutable transfer
history.

Migration `20260801_0007` implements shifts, employee/branch shift assignments,
and dated shift exceptions. Shifts persist server-derived overnight state,
working weekdays, grace/break rules, effective range, recurrence, active state,
and optimistic version. Assignment rows target exactly one same-tenant employee
or branch and are checked for effective-range overlap before write. Exceptions
provide one tenant-bound override per shift/date.

## Attendance

- `attendance_records`: one calculated work session with employee, branch,
  shift, check-in/out, method, classification, durations and approval data.
- `attendance_events`: immutable raw check-in/out evidence and validation
  result.
- `attendance_corrections`: requested/applied before-and-after values, reason,
  attachment and actor/session metadata.
- `qr_tokens`: short-lived, hashed branch/shift token with use limits.
- `permission_requests`, `permission_approvals`: hourly/early-departure
  workflow and immutable decisions.
- `proof_of_presence_requests`, `proof_of_presence_responses`: target scope,
  deadline, requested evidence and verified result.

Idempotency keys and partial unique constraints prevent duplicate open sessions
and repeated attendance submissions. Server-side calculations use branch
coordinates and shift rules, never client-calculated distance or status.

## Tasks

- `tasks`, `task_assignees`, `task_comments`, `task_attachments`,
  `task_status_history`, and `task_read_receipts` support personal, group and
  branch work, chat-like updates, proof, read state and deadline extensions.

## Leave and documents

- `leave_types`, `leave_balances`, `leave_requests`, and `leave_approvals`
  maintain allowance transactions and approval history.
- `document_types`, `employee_documents`, and `document_reminders` maintain
  private employee documents, computed expiry state and notification schedules.

## Notifications, exports and audit

- `notifications` and `notification_preferences` store in-app delivery state.
- `export_jobs` stores tenant-scoped filters, output metadata and expiry.
- `audit_logs` stores immutable actor, tenant, action, target, before/after
  summaries, request ID, IP/device/session metadata and support-mode context.
- `outbox_events` and `scheduled_jobs` are introduced with reliable delivery
  milestones, not during empty scaffolding.

## SaaS billing

- `plans`, `plan_features`, `subscriptions`, `subscription_events`, `coupons`,
  `coupon_redemptions`, and `usage_counters` support trial, manual activation,
  monthly/annual periods, plan limits and later provider adapters.

Payment provider references remain nullable until a real provider is selected.
Manual activation is explicitly labeled and fully audited.

## Migration policy

Alembic is the only schema-change mechanism. Migrations must be forward-safe,
reviewed, tested against `haydar_test`, and documented with rollback or
roll-forward guidance. Destructive changes require a verified backup and a
separate maintenance plan.
