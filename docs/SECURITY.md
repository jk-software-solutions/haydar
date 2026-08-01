# Security

## Trust boundaries

The API and PostgreSQL database are authoritative. Flutter binaries, browser
code, GPS values, QR input, role visibility and cached data are untrusted.
Every sensitive action is authenticated, tenant-scoped, authorized and audited
on the server.

## Identity and sessions

- Hash passwords with Argon2id and configurable memory/time parameters.
- Normalize and uniquely index verified email/phone identities.
- Use short-lived access JWTs and rotating refresh sessions with hashed token
  identifiers, expiry, revocation, family linkage and reuse detection.
- Revoke sessions on secure logout, account deactivation, password reset and
  material security changes.
- Store mobile session material in Flutter Secure Storage and web session
  material in Secure, HttpOnly, SameSite cookies.
- Hash password reset and invitation tokens at rest and enforce one-time use.

## Authorization and tenancy

Permissions use stable domain/action pairs: view, create, edit, delete, approve,
export and manage. The API resolves an active company membership from the
session; request bodies never control tenant identity.

Repositories accept a required tenant context and apply it to reads and writes.
Composite constraints prevent cross-tenant references. Cross-company tests are
required before each tenant-owned module is complete. PostgreSQL RLS may be
added later as defense in depth and must not replace application policies.

The implemented invitation repository paths require a session-derived tenant
context and include `company_id` in every query. The inviter reference uses a
composite `(company_id, membership_id)` constraint. API tests create two real
companies in `haydar_test` and prove that list/detail reads cannot cross the
tenant boundary. Access tokens are accepted only while their referenced refresh
session, membership, user, and company are all active.

## Device and attendance security

Each installation creates a random identifier and device-held signing key.
The backend stores the public key, approval state and history. Sensitive
attendance requests require an active device and signed challenge/request.
Changing devices revokes the old approval after an audited workflow.

The server validates subscription, membership, assignment, shift window,
device, geofence, duplicate/open session and approved permissions. Raw evidence
is retained in immutable attendance events. Play Integrity is an adapter point,
not the sole security boundary.

## API and platform protections

- Strict Pydantic validation and allowlisted filtering/sorting.
- CORS allowlist, security headers, HTTPS in deployed environments and no
  secrets in logs.
- Request IDs and structured security/audit logging.
- Idempotency and database constraints around duplicate-prone actions.
- Rate limits by IP, session, user and device on authentication and attendance.
- Generic authentication recovery responses to reduce account enumeration.
- Confirmation and recent authentication for sensitive administrative actions.

## Files and exports

Validate size, MIME type, extension and file signature. Store private objects
under tenant-prefixed opaque keys, serve time-limited downloads, and exclude
original filenames from storage paths. Export filters and downloads are
tenant-scoped and audited.

## Secrets

Real values live only in ignored `.env` files locally and a secret manager in
production. `.env.example` contains placeholders. Git staging is checked for
secret and generated-file patterns before every checkpoint.

## Support access

Super Admin support entry requires an explicit reason and expiry. Entry, every
privileged action and exit are recorded with the operator, target tenant,
request/session metadata and before/after summaries.

## Deferred integrations

Firebase, Maps, email/SMS, object storage, signing and payment credentials are
requested at their milestones. Unconfigured providers fail explicitly. No
adapter may report a successful external operation it did not perform.
