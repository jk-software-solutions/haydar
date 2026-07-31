# HADIR Web Portal

One Next.js portal hosts the Company Admin and Platform Super Admin areas.
Arabic is the default locale and English is available from the same application.

## Commands

```powershell
pnpm install --frozen-lockfile
pnpm lint
pnpm typecheck
pnpm test
pnpm build
pnpm dev
```

On the 8 GB development laptop, run these commands sequentially and set
`NODE_OPTIONS=--max-old-space-size=1536` for lint and production builds.

The `/[lang]/company` and `/[lang]/platform` route groups intentionally return
not-found until the real API-backed authentication and role policies are
implemented. No administrative content is exposed through a fake session.
