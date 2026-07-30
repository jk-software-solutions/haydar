# Architecture

## System shape

HADIR is a modular monolith with three deployable applications:

1. `apps/mobile`: one Flutter application for all company roles.
2. `apps/web`: one Next.js portal with Company Admin and Platform Super Admin
   route groups.
3. `services/api`: one FastAPI service containing domain modules, policies,
   repositories, integrations, and background work.

PostgreSQL is the business source of truth. Mobile and web clients never own
attendance rules, tenant selection, permissions, subscriptions, or audit data.

## Backend boundaries

```text
HTTP API -> authentication/tenant dependencies -> policies -> services
        -> tenant-scoped repositories -> SQLAlchemy -> PostgreSQL
        -> integrations/outbox -> email, FCM, storage, exports
```

- API handlers parse transport concerns and return stable REST contracts.
- Policies decide whether the authenticated membership may perform a
  domain/action operation.
- Services own transactions and business workflows.
- Repositories require an explicit tenant context for company-owned data.
- Integrations expose interfaces so local and managed providers share the same
  business behavior.

The application runs as one Uvicorn worker locally. FastAPI `BackgroundTasks`
handles short, non-critical follow-up work. Reliable delivery and scheduled
work will use a PostgreSQL transactional outbox and a lightweight worker when
the notification/export milestones require them.

## Tenant isolation

The authenticated access token identifies a user and session. The requested
company context must resolve to an active membership on the server. Client
payloads never select or override `company_id`.

Initial enforcement layers are:

- required tenant context dependencies;
- domain/action RBAC policies;
- tenant-scoped repository methods;
- `company_id` in composite uniqueness and foreign-key constraints;
- tenant-prefixed storage and export paths;
- tenant-aware background job payloads; and
- cross-tenant service and API tests.

PostgreSQL row-level security is a later defense-in-depth improvement after the
application-level model is proven. It is not a prerequisite for the MVP.

## Mobile architecture

The Flutter application uses feature-first modules, Riverpod state management,
GoRouter guards, Dio networking, Freezed/json serialization, and secure token
storage. Authenticated permissions generate navigation and action visibility.
An employee never receives a separate binary from a manager.

Attendance submissions always send raw device evidence—coordinates, accuracy,
method, device proof, and timestamps. The backend calculates distance, status,
lateness, and early departure. Attendance is not queued offline.

## Web architecture

The Next.js App Router application contains public/authentication routes,
Company Admin routes, and Platform Super Admin routes. Server-side route guards
provide the first access check; API authorization remains authoritative.
TanStack Query manages remote state, React Hook Form and Zod validate user
input, and translation keys drive all visible text.

## Storage and external services

Local development uses a private filesystem directory on F: through a storage
interface. Production uses an S3-compatible implementation with private
objects and signed downloads. Email, FCM, Maps, Play Integrity, and payment
providers remain explicit adapters. An unconfigured adapter fails clearly and
never simulates delivery.

## Deployment shape

Local development is native Windows without containers. Production uses a
managed PostgreSQL service, managed object storage, Nginx/TLS, and supervised
FastAPI and Next.js processes. Alembic migrations run as a release step before
new application processes receive traffic.
