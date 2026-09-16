#!/usr/bin/env bash
# Run on KODISRV to create the immotool postgres role/user/database and apply the baseline schema.
# Uses the shared postgres container (postgres-postgres-1) from the audiotool stack.
# Requires PLATFORM_ADMIN_PASSWORD and IMMOTOOL_PASSWORD in .env.
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

POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-postgres-postgres-1}"

run_psql() {
    PGPASSWORD="$PLATFORM_ADMIN_PASSWORD" \
    docker exec -i \
        -e PGPASSWORD="$PLATFORM_ADMIN_PASSWORD" \
        "$POSTGRES_CONTAINER" \
        psql --username=platform_admin "$@"
}

echo "Creating immotool_owner role, immotool user, and immotool database..."
run_psql --dbname=audiotool <<SQL
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
SQL

run_psql --dbname=audiotool -c "SELECT 1 FROM pg_database WHERE datname = 'immotool'" \
    | grep -q 1 \
    && echo "immotool database already exists, skipping CREATE" \
    || run_psql --dbname=audiotool -c "CREATE DATABASE immotool OWNER immotool_owner"

echo "Applying baseline schema..."
run_psql --dbname=immotool < "$PROJECT_DIR/migrations/001_initial.sql"

echo ""
echo "Done. Make sure .env contains:"
echo "  DATABASE_MODE=remote"
echo "  DATABASE_DSN=host=\$(docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' $POSTGRES_CONTAINER) dbname=immotool user=immotool password=\$IMMOTOOL_PASSWORD"
