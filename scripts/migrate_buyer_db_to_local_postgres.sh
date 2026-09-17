#!/usr/bin/env bash
# Start the local Compose database, import Buyer SQLite data once, then start the app.

set -euo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repository_root"

require_environment_variable() {
  local variable_name="$1"
  if [[ -z "${!variable_name:-}" ]]; then
    echo "$variable_name must be set" >&2
    exit 1
  fi
}

require_environment_variable "IMMOWBOT_INVITE_TOKEN"
require_environment_variable "IMMOWBOT_AUTH_SECRET"

if [[ ! -x .venv/bin/python ]]; then
  echo ".venv/bin/python is required; create the project virtual environment first" >&2
  exit 1
fi

if [[ ! -f data/buyer.db ]]; then
  echo "SQLite source database not found: $repository_root/data/buyer.db" >&2
  exit 1
fi

local_postgres_password="${LOCAL_POSTGRES_PASSWORD:-immotool_local_dev}"
local_postgres_port="${LOCAL_POSTGRES_PORT:-55433}"
compose=(docker compose -f docker-compose-mac-local.yml)
archive_dir="$repository_root/data/sqlite-rollback-archives"
postgres_dsn="postgresql://immotool:${local_postgres_password}@127.0.0.1:${local_postgres_port}/immotool"

mkdir -p "$archive_dir"

echo "Starting local PostgreSQL..."
"${compose[@]}" up -d --wait postgres

echo "Applying PostgreSQL schema..."
"${compose[@]}" run --build --rm --no-deps migrate

echo "Importing Buyer SQLite data..."
DATABASE_MODE=local DATABASE_DSN="$postgres_dsn" \
  .venv/bin/python scripts/import_sqlite_to_postgres.py \
    --sqlite-path "$repository_root/data/buyer.db" \
    --archive-dir "$archive_dir"

echo "Starting Immowbot..."
"${compose[@]}" build app
"${compose[@]}" up -d --no-build --no-deps app

echo "Local Immowbot is running at http://localhost:${LOCAL_APP_PORT:-666}"
