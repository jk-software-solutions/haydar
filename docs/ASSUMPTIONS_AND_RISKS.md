# Assumptions and Risks

## Locked assumptions

- Repository and technical naming is `haydar`; the visible name is
  `HADIR | حاضر`.
- The Android application ID is `com.jawadsites.haydar`.
- One Flutter application supports every company role.
- One Next.js application contains both administrative portals.
- Existing PostgreSQL 18 is reused only after authenticated health checks.
- Tenant isolation begins in application dependencies, policies, repositories,
  constraints and tests. PostgreSQL RLS is deferred defense in depth.
- Manual subscription activation is real and audited until a payment provider
  is selected.
- Android is the Day 30 publication target; iOS remains source-compatible but
  is not released in the MVP.

## Current risks and mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Only ~8 GB RAM and low free memory | Builds may stall or be killed | Run checks sequentially; one Uvicorn worker; stop unused processes |
| Limited free space on C: | SDK/package caches may fill the system drive | Put project, virtualenv, caches, data and artifacts on F: |
| PostgreSQL admin password unavailable to automation | Database/role creation may pause | Complete independent work; request local credential entry only at DB checkpoint |
| Existing PostgreSQL cluster contains unrelated data | An unsafe setup could damage other projects | Read-only health check first; create new DBs/roles only; never alter existing data |
| No USB Android device connected | Plugin/runtime checks cannot be proven | Continue static/build checks; defer runtime claim and main promotion as appropriate |
| 30-day scope is broad | Incomplete or weakly tested features | Keep status honest, finish foundations, prioritize mandatory flows, avoid extras |
| External provider credentials arrive late | Notifications/maps/storage/release can slip | Request each credential at its scheduled milestone; explicit disabled states |
| GPS spoofing or weak device identity | Fraudulent attendance | Server validation, device key proof, audit evidence and Play Integrity adapter |
| Tenant filter regression | Cross-company data exposure | Central tenant context, scoped repositories, composite constraints and isolation tests |
| Complex overnight/exception shifts | Incorrect attendance classification | Pure calculation services plus boundary/timezone tests |

## Explicit exclusions

- Docker, Docker Compose, Kubernetes, Redis and Celery during foundation.
- SQLite as a PostgreSQL replacement.
- Android emulators.
- Multiple mobile applications.
- Advanced face recognition, payroll, deep biometric identity, AI, WhatsApp,
  ERP integrations and full offline-first synchronization.
- Live payment gateway until a provider is selected.
- Native iOS publication and a large marketing CMS.

## Credentials not required on Day 1

Google Maps, Firebase/FCM, email/SMS, S3-compatible storage, Android signing,
domain/TLS and production service credentials are requested only when their
integration begins. Missing values must cause explicit configuration errors or
disabled features—not mocked success.

## Real blockers

A blocker is recorded only after a required command or integration is attempted
and an external dependency prevents safe progress. Low memory, missing future
credentials, or an absent Android device do not block independent foundation
work.
