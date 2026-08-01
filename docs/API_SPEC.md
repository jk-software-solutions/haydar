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
