#!/usr/bin/env bash
# Run on KODISRV to create the immotool postgres role/user/database and apply the baseline schema.
# Requires PLATFORM_ADMIN_PASSWORD and IMMOTOOL_PASSWORD in .env (same file used by compose.yml).
#
# Usage (from the immowbot project directory on KODISRV):
#   bash scripts/setup_immotool_postgres.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Load .env
set -a
source "$PROJECT_DIR/.env"
set +a

: "${PLATFORM_ADMIN_PASSWORD:?PLATFORM_ADMIN_PASSWORD not set in .env}"
: "${IMMOTOOL_PASSWORD:?IMMOTOOL_PASSWORD not set in .env}"

run_psql() {
    PGPASSWORD="$PLATFORM_ADMIN_PASSWORD" \
    docker compose --env-file "$PROJECT_DIR/.env" -f "$PROJECT_DIR/compose.yml" exec -T \
        -e PGPASSWORD="$PLATFORM_ADMIN_PASSWORD" postgres \
        psql --username=platform_admin --dbname=postgres "$@"
}

echo "Creating immotool_owner role, immotool user, and immotool database..."
run_psql <<SQL
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'immotool_owner') THEN
        CREATE ROLE immotool_owner NOLOGIN;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'immotool') THEN
        CREATE USER immotool WITH PASSWORD '$IMMOTOOL_PASSWORD';
        GRANT immotool_owner TO immotool;
    END IF;
END
\$\$;
SELECT datname FROM pg_database WHERE datname = 'immotool';
SQL

# Create database separately (cannot run inside a transaction block)
PGPASSWORD="$PLATFORM_ADMIN_PASSWORD" \
docker compose --env-file "$PROJECT_DIR/.env" -f "$PROJECT_DIR/compose.yml" exec -T \
    -e PGPASSWORD="$PLATFORM_ADMIN_PASSWORD" postgres \
    psql --username=platform_admin --dbname=postgres \
    -c "SELECT 1 FROM pg_database WHERE datname = 'immotool'" \
    | grep -q 1 && echo "immotool database already exists, skipping CREATE" || \
PGPASSWORD="$PLATFORM_ADMIN_PASSWORD" \
docker compose --env-file "$PROJECT_DIR/.env" -f "$PROJECT_DIR/compose.yml" exec -T \
    -e PGPASSWORD="$PLATFORM_ADMIN_PASSWORD" postgres \
    psql --username=platform_admin --dbname=postgres \
    -c "CREATE DATABASE immotool OWNER immotool_owner"

echo "Applying baseline schema..."
PGPASSWORD="$PLATFORM_ADMIN_PASSWORD" \
docker compose --env-file "$PROJECT_DIR/.env" -f "$PROJECT_DIR/compose.yml" exec -T \
    -e PGPASSWORD="$PLATFORM_ADMIN_PASSWORD" postgres \
    psql --username=platform_admin --dbname=immotool \
    < "$PROJECT_DIR/migrations/001_initial.sql"

echo "Done. Add to .env on KODISRV:"
echo "  DATABASE_MODE=local"
echo "  DATABASE_PASSWORD=$IMMOTOOL_PASSWORD"
echo "  POSTGRES_SOCKET_HOST_DIR=/var/run/postgresql"
