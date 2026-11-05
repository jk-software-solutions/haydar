# API Specification

## Base contract

- Base path: `/api/v1`
- JSON uses `snake_case`.
- Identifiers are UUID strings.
- Timestamps are ISO-8601 UTC strings.
- Administrative lists return `items`, `page`, `page_size`, and `total`.
- Activity feeds use an opaque `cursor` and `next_cursor`.
- Sorting is restricted to endpoint allowlists.
- Request IDs are accepted/generated through `X-Request-ID` and returned on
  every response.

Tenant identity is resolved from the authenticated session and selected active
membership. Company-owned write payloads do not expose `company_id`.

## Errors

Errors use `application/problem+json` with:

```json
{
  "type": "https://api.haydar/errors/validation",
  "title": "Request validation failed",
  "status": 422,
  "code": "validation_error",
  "detail": "One or more fields are invalid.",
  "request_id": "uuid",
  "field_errors": []
}
```

Stable codes distinguish authentication, authorization, tenant, subscription,
device, geofence, shift, conflict, idempotency and integration failures.

## Authentication contract

- `POST /auth/register-company`
- `POST /auth/login`
- `POST /auth/refresh`
- `POST /auth/logout`
- `POST /auth/password/forgot`
- `POST /auth/password/reset`
- `POST /auth/invitations/activate`
- `GET /auth/session`
- `DELETE /auth/sessions/{session_id}`

Access tokens are short-lived JWTs. Refresh tokens rotate on use and map to a
revocable database session. Mobile stores session material in secure storage;
the web server layer stores it in Secure, HttpOnly, SameSite cookies.

## Resource groups

The versioned API includes:

- `/companies`, `/memberships`, `/roles`, `/permissions`, `/employees`
- `/invitations`
- `/devices`, `/branches`, `/shifts`
- `/attendance`, `/attendance/manual`, `/attendance/history`
- `/permission-requests`, `/proof-of-presence`
- `/tasks`, `/leave`, `/documents`
- `/notifications`, `/reports`, `/exports`
- `/plans`, `/subscriptions`, `/coupons`
- `/super-admin`, `/support-mode`, `/audit-logs`
- `/health/live`, `/health/ready`

Exact endpoint request/response schemas are added alongside each implemented
module and generated in OpenAPI. Routes unavailable in the current milestone
are not registered as fake successes.

### Implemented invitation contract

- `POST /invitations` creates a tenant-scoped, expiring invitation for Manager,
  Supervisor, HR Officer, or Employee. It requires `members:create`.
- `GET /invitations?page=1&page_size=25` returns the current tenant's paginated
  invitations and requires `members:view`.
- `GET /invitations/{invitation_id}` returns only an invitation belonging to
  the authenticated tenant; another tenant receives `invitation_not_found`.
- `POST /auth/invitations/activate` consumes the one-time activation token,
  creates the user and membership, and returns a real access/refresh session.

The create payload forbids unknown fields, including `company_id`. During local
development the activation token is returned once to support manual delivery;
the later email/SMS milestone will deliver the same real token through the
configured provider without storing its plaintext value.

### Implemented device contract

- `POST /devices/register` registers the authenticated membership's installation;
  the first device is approved, while replacements require a reason and review.
- `GET /devices/me` returns only the authenticated membership's device history.
- `GET /devices/change-requests` returns a paginated, tenant-scoped reviewer queue.
- `POST /devices/change-requests/{id}/approve` revokes the previous device and
  approves the requested replacement atomically.
- `POST /devices/change-requests/{id}/reject` rejects the request and revokes the
  pending installation.

The API never accepts membership or company identity in device payloads.

### Implemented organization contract

- `GET /companies/current` returns settings for the authenticated company only.
- `PATCH /companies/current` updates display name, default locale, timezone, and
  country code; it requires `settings:manage` and the current optimistic
  `version`.
- `GET /employees/me` returns the current membership's own tenant profile.
- `GET /employees?page=1&page_size=25&search=` returns a permission-gated,
  tenant-scoped employee list.
- `GET /employees/{membership_id}` returns an employee only when the membership
  belongs to the authenticated tenant.
- `PATCH /employees/{membership_id}` updates employment profile fields, requires
  `members:manage`, and rejects stale versions with `concurrency_conflict`.

Company and employee write payloads forbid `company_id`. Cross-tenant identifiers
are indistinguishable from missing resources, and successful settings/profile
updates append immutable audit events.

### Implemented branches and departments contract

- `/branches` supports tenant-scoped create, paginated list, detail, versioned
  update, and soft archive. Branch payloads include code, Saudi short/full
  address, coordinates, geofence radius, timezone, working hours, optional
  authorized Wi‑Fi networks (`SSID` plus `BSSID`), and optional same-tenant
  owner/manager-role manager membership.
- `GET /branches/management/supervisors` lists visible branch supervisor mappings.
  `PUT /branches/{branch_id}/supervisors` atomically replaces the branch's active
  supervisor-role members using the branch version and writes an audit event.
- `/departments` supports tenant-scoped create, list, detail, versioned update,
  hierarchy, and soft archive.
- `POST /branches/assignments` creates an initial employee assignment or closes
  the current effective period and creates an auditable transfer.
- `GET /branches/assignments/me` returns only the authenticated membership's
  history; `GET /branches/assignments/{membership_id}` requires
  `assignments:view` and resolves the membership inside the current tenant.

Branch coordinates and radius are validated in both API schemas and PostgreSQL
constraints. Codes are unique inside a company, only one current branch
assignment can exist per membership, and write payloads forbid `company_id`.

### Implemented shifts contract

- `/shifts` supports tenant-scoped create, paginated list, detail, optimistic
  update, and soft archive.
- Shift writes accept local start/end times, unique weekday numbers `0..6`,
  grace/break minutes, effective range, and recurrence metadata. The server
  computes `is_overnight`; clients cannot supply it.
- `POST /shifts/assignments` assigns one shift to either an employee or branch
  for an effective range and rejects any overlapping target assignment.
- `GET /shifts/assignments/me` returns the authenticated employee's direct shift
  assignments only.
- `POST /shifts/{shift_id}/exceptions` records a non-working day or paired
  start/end override; duplicate shift/date exceptions are rejected.

Shift, employee, branch, assignment actor, and exception references are bound by
composite tenant constraints. Assignment dates must remain inside the selected
shift's effective period.

## Concurrency and idempotency

`Idempotency-Key` is mandatory for check-in/out, manual corrections, device
changes, export creation and subscription events. Keys are scoped to tenant,
actor and operation, persist the result fingerprint, and reject reuse with a
different payload.

Approval/correction writes include the current aggregate `version`. Stale
versions return HTTP 409 with `concurrency_conflict`.

## Files

Uploads are multipart requests with server-side type, extension, signature and
size validation. Files are private and tenant-prefixed. Responses expose file
metadata rather than permanent public URLs; downloads use short-lived signed
authorization.

## Attendance evidence

Attendance requests include branch/shift intent, device proof, observed
coordinates, accuracy, client observation time and method. The server resolves
assignments and calculates distance, time window and final classification.
Client-supplied distance, lateness or status fields are rejected.

## Super Admin and support mode

Platform routes require `SUPER_ADMIN`. Company support access requires a
time-bounded support session with reason, target company and immutable audit
events. Support context never changes the user into an unaudited company member.
# Implemented operations API extension

All routes below are under `/api/v1`, require a tenant bearer session unless noted, reject
client-supplied tenant ownership, and return RFC 9457-style problem responses.

- Attendance: `POST /attendance/check-in`, `POST /attendance/check-out`, `GET /attendance/me`,
  `GET /attendance`, `GET /attendance/records/{id}/location-events`,
  `POST /attendance/manual`, `PATCH /attendance/{id}`,
  `POST /attendance/qr-tokens`, and `POST /attendance/reconcile`.
  Check-in/out methods are `gps`, `qr`, or `wifi`. Wi‑Fi actions include the
  current network SSID and BSSID configured for the employee's branch and do
  not require geofence coordinates.
- Permission requests: `POST/GET /permission-requests` and
  `POST /permission-requests/{id}/review`.
- Presence: `POST/GET /presence-requests` and `POST /presence-requests/{id}/respond`.
- Tasks: `POST/GET /tasks`, `GET/PATCH /tasks/{id}`, `POST /tasks/{id}/status`, and
  `POST/GET /tasks/{id}/comments`.
- Leave: `POST/GET /leave/types`, `PUT/GET /leave/balances`, `POST/GET /leave/requests`, and
  `POST /leave/requests/{id}/review`.
- Documents and files: `POST/GET /documents`, `GET/PATCH/DELETE /documents/{id}`,
  `POST /documents/{id}/review`,
  `POST /files`, and `GET /files/{id}`. Uploads are limited to 10 MiB, validated by media type,
  subscription storage allowance, tenant, and employee ownership.
- Notifications: list/unread count, read-one/read-all, preferences, push-token registry and provider
  status under `/notifications`.

Authentication accepts `identifier` (normalized email or administrator-verified E.164 phone) plus
password; the legacy `email` request key remains accepted for compatibility. Company registration
creates the owner session and trial. Platform APIs include versioned plan CRUD, restricted coupons,
idempotent subscription activation, session-revoking suspension, and support-mode list/exit.

Attendance QR administration includes create/list/revoke/rotate. Rotation revokes every active token
for that branch in the same transaction. Task status updates that request more time require a reason
and requested due date; `/tasks/{id}/extension-decision` records the manager decision and approved
due date.
Proof of Presence creation accepts individual membership IDs, a branch, a group, or a union of
those targets. Manager listing returns each recipient result and server-computed distance; the
maintenance job persists expired pending recipients as `no_response`.
- Reports: `GET /reports/overview`, dedicated attendance/geofence/leave/permissions/tasks/documents
  datasets with member/branch/department/group/period/status filters, configurable leaderboard
  settings/list, `POST/GET /reports/exports`, explicit export cleanup, and authenticated download.
  Export responses include a seven-day `expires_at`; expired binary content is removed and download
  returns `410 export_expired`.
- Billing: public `GET /billing/plans`, tenant `GET /billing/subscription`, coupon validation,
  and payment-provider capability status.
- Platform: dashboard, company list/status/plan management, coupon management, support sessions,
  settings, and audit access under `/platform`; access requires a configured platform-admin email.

Attendance mutations additionally require `X-Installation-ID` for the currently approved device.
GPS distance and QR expiry/branch checks occur on the server. Export and file downloads are resolved
under the authenticated company and return 404 across tenant boundaries.
Company settings expose `attendance_biometric_policy` as `disabled`, `optional`, or `required`.
Required mode rejects attendance declarations without local confirmation; the boolean is retained
as event metadata and must not be interpreted as hardware-backed remote attestation.
