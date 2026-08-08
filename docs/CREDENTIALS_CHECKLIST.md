# Client-Owned Credentials and Access Checklist

Secrets are supplied through the deployment secret store or ignored local files. Never paste real
values into Git, tickets, screenshots, test fixtures, or this checklist.

| Boundary | Client-owned inputs required | Validation before PASS | Status |
|---|---|---|---|
| Production hosting | SSH host/user/key, final domain/DNS, Linux service identity, release paths | Deploy intended commit; verify HTTPS health/readiness and service working directories | BLOCKED |
| PostgreSQL | App/migrator/admin URLs and roles, TLS policy, backup destination/encryption | Least-privilege checks, migration, backup and isolated restore drill | BLOCKED |
| Firebase/FCM | Project ID, server service-account path, Android `google-services.json`, package/SHA restrictions | Provider status, server delivery/retry, real-device receipt and deep link | BLOCKED |
| Password email | SMTP host/port, sender, relay username/password or approved relay, public reset URL | Non-enumerating request and real inbox delivery/reset | BLOCKED |
| Google Maps | Web/Android key restricted to authorized origins, package and signing SHA | Picker persistence and restricted-key test on web/physical device | BLOCKED |
| Object storage | Private bucket, endpoint/region, access key/secret, encryption, CORS, retention | Tenant-safe upload/download/delete and denied public access | BLOCKED |
| Payment provider | Selected provider, merchant account, API keys, webhook secret and callback URLs | Signed webhook, replay/idempotency, refund/failure lifecycle | BLOCKED |
| Android signing | Upload keystore path, alias/passwords, final application ID and HTTPS API URL | Signed APK/AAB inspection and installation | BLOCKED by deferred build |
| Google Play | Client Play Console, support contact, privacy URL, listing assets and Data Safety decisions | Closed-track upload, pre-launch report and install | BLOCKED |
| GitHub Actions | Repository/account capable of scheduling Actions and environment secrets | Green backend/web/Flutter workflow | BLOCKED |

The implemented local adapters and status endpoints must continue reporting `not_configured` or
`BLOCKED` until the corresponding row is supplied and verified.
