"""Apply checked-in PostgreSQL migrations; runtime code never creates schema."""
from pathlib import Path
import hashlib
import psycopg

MIGRATIONS_DIR = Path(__file__).parents[2] / "migrations"

def apply_migrations(dsn, owner_role="immotool_owner"):
    applied = []
    with psycopg.connect(dsn) as connection:
        if owner_role:
            connection.execute("SET ROLE " + owner_role)
        connection.execute("CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())")
        known = {row[0] for row in connection.execute("SELECT version FROM schema_migrations")}
        for path in sorted(MIGRATIONS_DIR.glob("*.sql")):
            if path.name in known:
                continue
            connection.execute(path.read_text())
            connection.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (path.name,))
            applied.append(path.name)
    return applied
