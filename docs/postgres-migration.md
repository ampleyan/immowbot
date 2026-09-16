# PostgreSQL Migration Guide

This guide describes the one-time procedure to migrate from SQLite to the production PostgreSQL database.

## Prerequisites

You need:

1. A Linux or Mac environment with Python 3.12+ and access to the Immowbot repository
2. PostgreSQL running locally with a Unix socket (default `/var/run/postgresql`) or a remote `kodisrv` database
3. Environment variables configured for your target database:
   - **Local mode** (`DATABASE_MODE=local`): requires `DATABASE_PASSWORD` environment variable for local authentication
   - **Remote mode** (`DATABASE_MODE=remote`): requires `DATABASE_DSN` environment variable configured with host `kodisrv`, `sslmode=verify-full`, and an `sslrootcert` pointing to a local CA certificate file

## Step 1: Set up the baseline PostgreSQL schema

The baseline schema must be applied once to an empty `immotool` database before importing.

**Local mode (Unix socket):**

```bash
DATABASE_MODE=local \
DATABASE_PASSWORD="<your-password>" \
python scripts/migrate_postgres.py
```

**Remote mode (kodisrv):**

Configure `DATABASE_DSN` with your credentials (host must be `kodisrv`, user and database must be `immotool`, and `sslmode` must be `verify-full`):

```bash
DATABASE_MODE=remote \
DATABASE_DSN="<your-dsn>" \
python scripts/migrate_postgres.py
```

Expected output:
```
Applied: 001_initial.sql
```

Or if already applied:
```
Schema up to date
```

## Step 2: Import data from SQLite

Once the baseline schema is in place, import your SQLite database:

```bash
DATABASE_MODE=local \
DATABASE_PASSWORD="<your-password>" \
python scripts/import_sqlite_to_postgres.py \
  --sqlite-path /path/to/buyer.db \
  --archive-dir /path/to/archive/directory
```

The importer will:
1. Validate the SQLite file integrity
2. Create an immutable, content-addressed archive copy in `--archive-dir`
3. Import all tables in dependency order
4. Validate row counts and foreign keys
5. Print the archive filename and per-table counts

The original SQLite file is never modified or deleted.

**Example output:**
```
import completed — archive: immowbot-archive-20260916-abc123def.sqlite3
table counts:
  users: 1
  listings: 1247
  listing_versions: 3156
  alerts: 45
  property_lists: 8
  ...
```

## Step 3: Archive maintenance

Rollback archives are retained for at least 30 days. To delete archives older than 30 complete days:

```bash
python scripts/prune_sqlite_rollback_archives.py \
  --archive-dir /path/to/archive/directory
```

This command only deletes files matching the archive pattern and never touches the original SQLite source.

## Step 4: Verify in test environment

Before pointing your application at the production database, test the PostgreSQL connection and data:

```bash
docker compose -f docker-compose.test.yml up -d --wait
```

This starts a fresh disposable PostgreSQL instance for testing. Run your application and verify:
- All listings load correctly
- Search and filtering work as expected
- Scoring calculations are accurate
- No database connection errors

After testing, stop the container:

```bash
docker compose -f docker-compose.test.yml down
```

## Step 5: Point the application at PostgreSQL

Update your deployment environment to use PostgreSQL:

**For local (Docker on Linux with Unix socket):**

```bash
DATABASE_MODE=local \
DATABASE_PASSWORD="<your-password>" \
docker compose up --build -d
```

**For remote (kodisrv on Raspberry Pi):**

```bash
DATABASE_MODE=remote \
DATABASE_DSN="<your-dsn>" \
docker compose up --build -d
```

Where your `DATABASE_DSN` uses host `kodisrv`, user and database `immotool`, `sslmode=verify-full`, and references a local CA certificate file.

Verify the application connects and displays data correctly.

## Rollback procedure

If you need to revert to SQLite:

1. Stop the application
2. Restore the original SQLite file or extract from an archive in `--archive-dir`
3. Update your deployment to use SQLite instead of PostgreSQL
4. Restart the application

Archives are immutable (mode `0444`) and never overwritten, ensuring you can always recover the data state at import time for at least 30 days.

## Important: separate operator authorization

The following actions require explicit separate authorization and cannot be automated or assumed:

1. **Live Pi execution** — Deploying to the production Raspberry Pi
2. **Secret provisioning** — Supplying or rotating database passwords and certificates
3. **Source SQLite deletion** — Removing the original `data/buyer.db` or archives

No deployment script, importer, or maintenance tool performs these actions. They are always manual operator decisions.
