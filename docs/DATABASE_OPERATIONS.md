# Database operations

HADIR uses PostgreSQL with separate runtime and migration identities. The runtime user must not own
the schema. Migrations are forward-reviewed Alembic revisions; the current development head is
`20260808_0012`.

## Release migration

1. Confirm the application artifact and target revision.
2. Create and verify a custom-format backup.
3. Run `python -m alembic upgrade head` with `MIGRATION_DATABASE_URL`.
4. Run `python -m alembic current` and `/api/v1/health/ready`.
5. Start the new API and run tenant-isolation/authenticated smoke tests.

Do not automatically downgrade a production schema. If a release must be rolled back, restore the
previous application artifact when schema-compatible or apply a reviewed forward repair.

## Backup and restore

Linux production uses `deploy/scripts/backup-postgres.sh`; Windows validation uses
`scripts/backup-postgres.ps1`. Both create custom-format archives, verify that PostgreSQL can list
them, and record SHA-256. Retain managed snapshots/PITR in addition to logical exports.

Restore only into an explicitly named empty validation database first. Use
`deploy/scripts/restore-postgres.sh` or `scripts/restore-postgres.ps1 -WhatIf` followed by a
confirmed restore. Validate table counts, migrations, tenant foreign keys, and application
readiness before considering a backup usable.
