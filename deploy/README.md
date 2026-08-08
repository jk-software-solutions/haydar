# HADIR production deployment bundle

This directory is a reviewed template for a single Linux host or small VM. Replace every
`example.com` and `CHANGE_ME` value before installation.

1. Create the `hadir` system user and `/opt/hadir/releases`, `/opt/hadir/current`,
   `/etc/hadir`, `/var/lib/hadir`, `/var/log/hadir`, and `/var/backups/hadir` directories.
2. Install Python 3.12, Node 24, pnpm 10, PostgreSQL client tools, Nginx, and Certbot.
3. Copy a tested source release under `/opt/hadir/releases/<release-id>` and point the
   `current` symlink to it.
4. Create the API virtual environment and install `services/api` with
   `python -m pip install .`.
5. Install web dependencies with the frozen lockfile and run `pnpm build`.
6. Put secrets in root-owned `/etc/hadir/api.env` and `/etc/hadir/web.env` with mode 0640.
7. Back up PostgreSQL, run `python -m alembic upgrade head` using the migration identity,
   and confirm `python -m alembic current` shows the expected head.
8. Install the systemd units and timer from `systemd/`, then enable them.
9. Replace the hostnames and certificate paths in `nginx/hadir.conf`, test with `nginx -t`,
   and reload Nginx only after the test succeeds.
10. Verify `/api/v1/health/live`, `/api/v1/health/ready`, Arabic and English web routes,
    systemd process working directories, and a real authenticated workflow.

The API binds only to loopback. PostgreSQL must not be publicly reachable. TLS certificates,
DNS, production database credentials, platform-admin emails, Firebase configuration, Google
Maps key, and the final Android API URL are deployment inputs and are never committed.
