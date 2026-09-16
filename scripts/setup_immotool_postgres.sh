#!/usr/bin/env bash
# Run on KODISRV to create the immotool postgres role/user/database and apply the baseline schema.
# Postgres runs as a system service on the host (not in Docker).
# Requires IMMOTOOL_PASSWORD in .env.
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

: "${IMMOTOOL_PASSWORD:?IMMOTOOL_PASSWORD not set in .env}"

run_psql() {
    sudo -u postgres psql "$@"
}

echo "Creating immotool_owner role, immotool user, and immotool database..."
run_psql --dbname=postgres <<SQL
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

run_psql --dbname=postgres -c "SELECT 1 FROM pg_database WHERE datname = 'immotool'" \
    | grep -q 1 \
    && echo "immotool database already exists, skipping CREATE" \
    || run_psql --dbname=postgres -c "CREATE DATABASE immotool OWNER immotool_owner"

echo "Applying baseline schema..."
run_psql --dbname=immotool < "$PROJECT_DIR/migrations/001_initial.sql"

echo ""
echo "Done. Make sure .env on KODISRV contains:"
echo "  DATABASE_MODE=local"
echo "  DATABASE_PASSWORD=$IMMOTOOL_PASSWORD"
echo "  POSTGRES_SOCKET_HOST_DIR=/var/run/postgresql"
