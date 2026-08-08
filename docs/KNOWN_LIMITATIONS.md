# Known limitations

- Firebase push delivery and embedded Google Maps are not activated until customer-owned credentials
  and final Android certificate restrictions are supplied. In-app notifications, GPS geofencing, and
  QR attendance are implemented without them.
- The payment provider is intentionally an adapter reporting `not_configured`; subscriptions can be
  activated manually until a provider is selected.
- The current protected-file implementation stores encrypted-at-rest-by-infrastructure binary data
  in PostgreSQL. A private S3-compatible adapter is recommended before high-volume document use.
- Rate limiting is process-local. Production Nginx also rate-limits; a Redis-backed distributed
  limiter is recommended when scaling API workers across hosts.
- Export jobs execute synchronously while persisting progress/status. Move them to a durable queue for
  very large tenants.
- Full offline synchronization, server-side face recognition, payroll, ERP/HR integrations,
  WhatsApp, iOS/App Store, and a marketing CMS are outside MVP scope.
- Final signed Play artifacts must be rebuilt by the release owner with the real production HTTPS API
  URL. A placeholder endpoint is deliberately rejected by the release script.
