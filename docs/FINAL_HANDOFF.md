# Final handoff checklist

## Delivered in source

- One role-aware Flutter app with Arabic/English, GPS and QR attendance, local biometric confirmation,
  tasks, requests, leave, document upload, and manager workspaces.
- Next.js company and platform portals with operations, reports/exports, subscription information,
  coupons, support mode, and platform controls.
- FastAPI/PostgreSQL multi-tenant backend through Alembic head `20260808_0022`, protected files,
  audit/security middleware, reporting, subscription limits, and scheduled maintenance.
- Nginx, systemd, environment, backup/restore, signing, and release-build templates.
- Administrator, platform owner, database, Play, privacy, support, limitations, and roadmap guides.

## Release-owner actions still requiring external authority

1. Supply production database, domain/DNS/TLS, platform-admin email, support/legal identity, and final
   HTTPS API URL.
2. Deploy the tested release and verify live/ready plus authenticated company and platform flows.
3. Supply Firebase/Maps credentials only if those optional transports/UI integrations are enabled.
4. Securely back up the generated Android upload key.
5. Run `scripts/build-android-release.ps1` with the real URL, test the resulting APK on a physical
   device, upload the AAB to Play internal testing, complete Data safety, and submit.

Do not label placeholder-domain artifacts, unverified backups, or an unsubmitted Play listing as
production-complete.
