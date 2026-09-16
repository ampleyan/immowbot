# SQLite-to-PostgreSQL Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace Immowbot's SQLite runtime with the existing `immotool` PostgreSQL database and provide a safe, one-shot SQLite importer plus immutable rollback archives.

**Architecture:** The application obtains a validated PostgreSQL DSN from `DATABASE_MODE` and passes it to a PostgreSQL-only `PropertyStore`. A versioned SQL baseline owns schema creation; the application never auto-creates or repairs schema. A separate importer reads an explicit SQLite source read-only, creates an immutable archive, and imports all rows into an empty baseline database in one PostgreSQL transaction.

**Tech Stack:** Python 3.12, psycopg 3, PostgreSQL 18, SQLite read-only fixtures, Docker Compose test service, `unittest`.

**Spec:** `docs/superpowers/specs/2026-09-16-sqlite-to-postgres-migration-design.md`

## Global Constraints

- Target only existing database/user `immotool`; migrations run under `immotool_owner`, runtime uses `immotool`.
- `DATABASE_MODE` must be `local` or `remote`; no SQLite runtime fallback is permitted.
- Local mode uses `/var/run/postgresql` Unix socket only; remote mode permits only `kodisrv` with `sslmode=verify-full` and an explicit CA file.
- Do not contact `kodisrv`, install on the Pi, import live data, modify production secrets, or delete SQLite source files.
- Preserve every current table, row, ID, relationship, JSON payload, timestamp meaning, unique constraint, and behavior.
- SQLite rollback archives are atomically published, immutable, never overwritten, and retained for at least 30 full days.
- Never log or print passwords, DSNs, or certificate contents.

---

### Task 1: Disposable PostgreSQL test environment and safe configuration

**Files:**
- Modify: `requirements.txt`
- Create: `docker-compose.test.yml`
- Create: `tests/postgres_support.py`
- Create: `tests/test_database_config.py`
- Modify: `src/buyer/database.py`
- Modify: `docker-compose.yml`
- Modify: `docker-compose-mac.yml`

**Interfaces:**
- Produces `DatabaseSettings(mode: str, dsn: str)` and `load_database_settings(environ: Mapping[str, str]) -> DatabaseSettings`.
- Produces `postgres_test_dsn() -> str`, `reset_postgres_database(dsn: str) -> None`, and `POSTGRES_TEST_DSN` test configuration.
- Consumes no production secret values; tests receive only a local disposable DSn.

- [ ] **Step 1: Write configuration failure tests**

```python
class DatabaseSettingsTest(unittest.TestCase):
    def test_local_mode_uses_unix_socket_not_tcp(self):
        settings = load_database_settings({
            "DATABASE_MODE": "local", "DATABASE_PASSWORD": "test-password",
        })
        self.assertIn("host=/var/run/postgresql", settings.dsn)
        self.assertNotIn("host=kodisrv", settings.dsn)

    def test_remote_mode_requires_verified_kodisrv_tls(self):
        with self.assertRaisesRegex(ValueError, "sslmode=verify-full"):
            load_database_settings({"DATABASE_MODE": "remote", "DATABASE_DSN": "host=kodisrv dbname=immotool user=immotool"})

    def test_invalid_or_unset_mode_fails_without_sqlite_fallback(self):
        for environ in ({}, {"DATABASE_MODE": "sqlite"}):
            with self.assertRaises(ValueError):
                load_database_settings(environ)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m unittest tests.test_database_config -v`

Expected: FAIL because `src.buyer.database` does not exist.

- [ ] **Step 3: Add psycopg and the disposable Compose service**

Add `psycopg[binary]` to `requirements.txt`. Create a `postgres-test` service in `docker-compose.test.yml` with an ephemeral named volume, a non-production password, a health check, and port binding only to `127.0.0.1`. Do not add it to production Compose.

- [ ] **Step 4: Implement validated settings and test utilities**

Implement strict parsing in `src/buyer/database.py`:

```python
@dataclass(frozen=True)
class DatabaseSettings:
    mode: Literal["local", "remote"]
    dsn: str

def load_database_settings(environ: Mapping[str, str] | None = None) -> DatabaseSettings:
    """Return a validated PostgreSQL configuration without logging secret fields."""
```

For local mode construct a keyword DSN with `host=/var/run/postgresql`, `dbname=immotool`, and `user=immotool`. For remote mode parse the supplied DSN with psycopg connection-info utilities, require host exactly `kodisrv`, database/user exactly `immotool`, `sslmode=verify-full`, and a non-symlink regular `sslrootcert`. Return validation errors without reproducing a DSn.

Provide test helpers that create a fresh test schema/database from `POSTGRES_TEST_DSN`; they must reject DSNs whose host is not loopback or whose database name lacks the `immowbot_test` prefix.

- [ ] **Step 5: Add Compose runtime configuration without secrets**

In production `docker-compose.yml`, pass `DATABASE_MODE`, `DATABASE_PASSWORD`, and safe connection-name variables through without defaults that select SQLite. Add an optional explicit host socket bind mount using `POSTGRES_SOCKET_HOST_DIR` to `/var/run/postgresql`. Keep the Mac Compose file remote-only/documented and do not add a Pi address or secret.

- [ ] **Step 6: Run configuration and Compose checks**

Run: `python -m unittest tests.test_database_config -v && docker compose -f docker-compose.test.yml config --quiet && docker compose config --quiet`

Expected: PASS; no output contains the test password or any DSN.

- [ ] **Step 7: Commit**

```bash
git add requirements.txt docker-compose.yml docker-compose-mac.yml docker-compose.test.yml src/buyer/database.py tests/postgres_support.py tests/test_database_config.py
git commit -m "feat: add validated postgres configuration"
```

### Task 2: Versioned PostgreSQL baseline and migration runner

**Files:**
- Create: `migrations/001_initial.sql`
- Create: `src/buyer/postgres_migrations.py`
- Create: `scripts/migrate_postgres.py`
- Create: `tests/test_postgres_baseline.py`

**Interfaces:**
- Produces `apply_migrations(dsn: str, owner_role: str = "immotool_owner") -> list[str]`.
- Consumes a disposable owner-capable test DSN and applies files in lexical version order.
- Produces all domain tables declared in the design spec and a `schema_migrations(version, applied_at)` ledger.

- [ ] **Step 1: Write baseline contract tests**

```python
def test_baseline_creates_all_domain_tables(self):
    apply_migrations(self.owner_dsn)
    self.assertEqual(table_names(self.runtime_dsn), {
        "alerts", "list_items", "listing_interactions", "listing_versions",
        "listing_workflow", "listings", "property_lists", "property_notes",
        "runs", "schema_migrations", "searches", "smart_lists", "source_runs", "users",
    })

def test_baseline_has_listing_version_foreign_keys_and_identity_ids(self):
    apply_migrations(self.owner_dsn)
    self.assertTrue(has_foreign_key(self.runtime_dsn, "listing_versions", "listing_id", "listings"))
    self.assertTrue(is_identity_column(self.runtime_dsn, "listings", "id"))
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `docker compose -f docker-compose.test.yml up -d --wait && POSTGRES_TEST_DSN='postgresql://immowbot_test:immowbot_test@127.0.0.1:55432/immowbot_test' python -m unittest tests.test_postgres_baseline -v`

Expected: FAIL because no migration runner or baseline exists.

- [ ] **Step 3: Write the baseline schema**

Translate `_SCHEMA` in `src/buyer/property_store.py` into `migrations/001_initial.sql`. Use quoted-safe static SQL only; `BIGINT GENERATED BY DEFAULT AS IDENTITY` for IDs, `BOOLEAN` for `is_admin`, `active`, `is_system`, and `enabled`, `NUMERIC` for `offer_amount`, `TIMESTAMPTZ` for stored times, and `JSONB` for `*_json` payloads. Preserve all natural-key unique constraints and explicit foreign keys, including `list_items.list_id`, `runs.search_id`, `source_runs.run_id`, `listing_versions.listing_id`, and `listing_versions.run_id`; preserve `ON DELETE CASCADE` for list items.

Add indexes for existing high-frequency predicates: user/name searches, listing source/natural IDs, listing-version current/history access, run/source-run joins, alert user ordering, and workflow/interactions natural keys.

- [ ] **Step 4: Implement the idempotent migration runner**

```python
def apply_migrations(dsn: str, owner_role: str = "immotool_owner") -> list[str]:
    """Apply unapplied local migration files once, transactionally, without logging dsn."""
```

Use one psycopg transaction per migration, create/read the migration ledger, execute `SET ROLE immotool_owner` only from the owner connection, and store the file version/checksum. Reject changed checksums for an already-applied version. The runtime store must not call this function.

- [ ] **Step 5: Run baseline tests and schema checks**

Run: `POSTGRES_TEST_DSN='postgresql://immowbot_test:immowbot_test@127.0.0.1:55432/immowbot_test' python -m unittest tests.test_postgres_baseline -v`

Expected: PASS, including a repeated-run test that applies no migration twice.

- [ ] **Step 6: Commit**

```bash
git add migrations/001_initial.sql scripts/migrate_postgres.py src/buyer/postgres_migrations.py tests/test_postgres_baseline.py
git commit -m "feat: add immotool postgres baseline"
```

### Task 3: PostgreSQL-only property store

**Files:**
- Modify: `src/buyer/property_store.py`
- Modify: `tests/test_property_store.py`
- Modify: `tests/test_alerts.py`
- Modify: `tests/test_collector.py`
- Modify: `tests/test_e2e_smoke.py`
- Modify: `tests/test_workflow.py`

**Interfaces:**
- Produces `PropertyStore(dsn: str)` backed by `psycopg.Connection` with `dict_row` results.
- Produces `get_runs_with_sources(search_id: int, limit: int) -> list[dict]` for callers that currently execute SQL directly.
- Consumes `POSTGRES_TEST_DSN` from `tests.postgres_support`.

- [ ] **Step 1: Port one behavior test to PostgreSQL and remove SQLite-configuration assertion**

```python
class PropertyStoreTest(PostgresDatabaseTestCase):
    def setUp(self):
        super().setUp()
        self.store = PropertyStore(self.runtime_dsn)

    def test_identical_observation_does_not_create_a_version(self):
        search_id = self.store.save_search(1, "home", "home", DEFAULT_HOME_SEARCH)
        run_id = self.store.start_run(search_id)
        self.store.save_listing(run_id, self.listing())
        self.store.save_listing(run_id, self.listing())
        self.assertEqual(self.store.version_count("immoweb", "123"), 1)
```

Remove assertions that SQLite uses WAL, busy timeout, SQLite table-rebuild migrations, or `PRAGMA foreign_key_check`; replace them with baseline and transaction behavior assertions.

- [ ] **Step 2: Run the selected test to verify it fails**

Run: `POSTGRES_TEST_DSN='postgresql://immowbot_test:immowbot_test@127.0.0.1:55432/immowbot_test' python -m unittest tests.test_property_store.PropertyStoreTest.test_identical_observation_does_not_create_a_version -v`

Expected: FAIL because the store still opens SQLite.

- [ ] **Step 3: Replace SQLite connection/migration code**

Remove `sqlite3`, `_SCHEMA`, `_run_user_migration`, `_repair_runs_foreign_key`, PRAGMAs, and `lastrowid`. Create a psycopg connection with `row_factory=dict_row`; use `with self.connection.transaction():` for every current atomic write block. Retain the public store method names and return shapes.

Convert SQL deliberately:

```python
cursor = self.connection.execute(
    "INSERT INTO users (username, password_hash, is_admin, created_at, alerts_since) "
    "VALUES (%s, %s, %s, %s, %s) RETURNING id",
    (username, pw_hash, is_admin, now, now),
)
return cursor.fetchone()["id"]
```

Use `ON CONFLICT (...) DO NOTHING`, PostgreSQL `EXCLUDED`, `string_agg`, and `payload_json->>'price'` casts. Map booleans and timestamps on the store boundary so existing JSON/API consumers continue receiving booleans and ISO-8601 strings. Do not make a generic SQL-rewrite layer.

- [ ] **Step 4: Add run-history store method and complete query conversion**

Implement `get_runs_with_sources` with `string_agg(sr.source || ':' || sr.status || ':' || sr.listing_count::text, '|' ORDER BY sr.id)`. Confirm every statement in `PropertyStore` uses `%s`; no qmarks, SQLite functions, or sqlite-specific exception type remain.

- [ ] **Step 5: Convert all store behavior tests**

Make each existing store, alert, collector, e2e, and workflow test inherit the disposable PostgreSQL fixture. Keep their behavioral assertions unchanged where possible. Add explicit tests for `RETURNING` IDs, duplicate idempotence, JSONB price-reduction behavior, transaction rollback, and timestamps as API-compatible strings.

- [ ] **Step 6: Run the converted behavior suite**

Run: `POSTGRES_TEST_DSN='postgresql://immowbot_test:immowbot_test@127.0.0.1:55432/immowbot_test' python -m unittest tests.test_property_store tests.test_alerts tests.test_collector tests.test_e2e_smoke tests.test_workflow -v`

Expected: PASS without creating any `.sqlite3` or `buyer.db` test database.

- [ ] **Step 7: Commit**

```bash
git add src/buyer/property_store.py tests/test_property_store.py tests/test_alerts.py tests/test_collector.py tests/test_e2e_smoke.py tests/test_workflow.py
git commit -m "feat: move property store to postgres"
```

### Task 4: Application integration and removal of direct dialect SQL

**Files:**
- Modify: `src/buyer/api.py`
- Modify: `src/buyer/dashboard.py`
- Modify: `src/buyer/scheduler.py`
- Modify: `tests/test_dashboard.py`
- Create: `tests/test_api_database_integration.py`

**Interfaces:**
- Consumes `load_database_settings()` and `PropertyStore(settings.dsn)`.
- Consumes `PropertyStore.get_runs_with_sources()`; neither API nor dashboard uses `store.connection.execute`.
- Background workers receive a validated DSN string, not a filesystem path.

- [ ] **Step 1: Write integration tests for runtime mode and run history**

```python
def test_api_store_uses_validated_database_settings(self):
    with patch.dict(os.environ, postgres_local_environ(self.runtime_dsn), clear=True):
        store = api.get_store()
    self.addCleanup(store.close)
    self.assertEqual(store.get_search_by_name(1, "antwerp-home"), None)

def test_run_history_is_returned_without_dashboard_sqlite_aggregation(self):
    rows = self.store.get_runs_with_sources(search_id, limit=5)
    self.assertEqual(rows[0]["sources"][0], {"source": "immoweb", "status": "ok", "count": 2})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `POSTGRES_TEST_DSN='postgresql://immowbot_test:immowbot_test@127.0.0.1:55432/immowbot_test' python -m unittest tests.test_api_database_integration tests.test_dashboard -v`

Expected: FAIL because API/dashboard still depend on `DB_PATH` and direct SQLite SQL.

- [ ] **Step 3: Replace path-based app wiring**

Remove `DB_PATH` constants and directory creation from API, dashboard, and scheduler. Each entrypoint calls `load_database_settings()` once and uses the validated DSn. Worker functions receive that DSn; never print it. Replace `sqlite3.IntegrityError` handling with `psycopg.IntegrityError` through a store-exported neutral exception alias or a narrow caught driver exception.

- [ ] **Step 4: Remove direct run-history queries**

Replace both `GROUP_CONCAT` call sites with `store.get_runs_with_sources`. Update dashboard worker/UI labels from `buyer.db` to a non-secret database label such as `PostgreSQL · immotool`.

- [ ] **Step 5: Run application integration tests**

Run: `POSTGRES_TEST_DSN='postgresql://immowbot_test:immowbot_test@127.0.0.1:55432/immowbot_test' python -m unittest tests.test_api_database_integration tests.test_dashboard tests.test_e2e_smoke -v`

Expected: PASS with no local SQLite database access.

- [ ] **Step 6: Commit**

```bash
git add src/buyer/api.py src/buyer/dashboard.py src/buyer/scheduler.py tests/test_dashboard.py tests/test_api_database_integration.py
git commit -m "feat: configure app for postgres runtime"
```

### Task 5: One-shot SQLite importer and immutable rollback archive management

**Files:**
- Create: `src/buyer/sqlite_importer.py`
- Create: `scripts/import_sqlite_to_postgres.py`
- Create: `scripts/prune_sqlite_rollback_archives.py`
- Create: `tests/test_sqlite_importer.py`
- Create: `tests/sqlite_fixture.py`

**Interfaces:**
- Produces `import_sqlite_to_postgres(sqlite_path: Path, postgres_dsn: str, archive_dir: Path) -> ImportReport`.
- Produces `prune_expired_archives(archive_dir: Path, now: datetime) -> list[Path]`.
- `ImportReport` exposes table counts and archive basename only; never its DSN/password.

- [ ] **Step 1: Write a complete SQLite fixture and importer success test**

```python
def test_import_preserves_ids_counts_and_relationships(self):
    source = create_complete_sqlite_fixture(self.tmp_path / "source.sqlite3")
    report = import_sqlite_to_postgres(source, self.runtime_dsn, self.archive_dir)
    self.assertEqual(report.table_counts["users"], 2)
    self.assertEqual(fetch_ids(self.runtime_dsn, "listing_versions"), [701, 702])
    self.assertEqual(fetch_payload(self.runtime_dsn, 701)["price"], 300000)
    self.assertEqual(postgres_foreign_key_violations(self.runtime_dsn), [])
```

The fixture must include at least two users; lists/list-items; notes; workflow; multiple interactions; alerts; smart lists; searches; runs; source runs; listings; two listing versions; non-default IDs; and representative JSON/timestamps.

- [ ] **Step 2: Add and run failure tests before implementation**

```python
def test_import_rejects_symlink_source_and_nonempty_target(self): ...
def test_import_rolls_back_target_rows_on_count_mismatch(self): ...
def test_archive_is_read_only_and_not_overwritten(self): ...
def test_pruning_keeps_archives_younger_than_thirty_full_days(self): ...
def test_errors_and_reports_do_not_contain_dsn_password(self): ...
```

Run: `POSTGRES_TEST_DSN='postgresql://immowbot_test:immowbot_test@127.0.0.1:55432/immowbot_test' python -m unittest tests.test_sqlite_importer -v`

Expected: FAIL because importer modules do not exist.

- [ ] **Step 3: Implement path validation and archive publication**

Require absolute, non-symlink regular source files and an existing, non-symlink archive directory. Read SQLite using URI read-only mode; require `PRAGMA integrity_check = 'ok'`, empty `foreign_key_check`, and the exact expected table/column contract. Copy with a staging name in the archive directory, `fsync`, atomic rename, and `chmod(0o444)`; publish a read-only JSON manifest containing source SHA-256, archive basename, timestamp, and counts. Never include connection strings.

- [ ] **Step 4: Implement the transactional importer**

```python
def import_sqlite_to_postgres(sqlite_path: Path, postgres_dsn: str, archive_dir: Path) -> ImportReport:
    source = validate_sqlite_source(sqlite_path)
    archive = publish_rollback_archive(source, archive_dir)
    with psycopg.connect(postgres_dsn) as target:
        with target.transaction():
            acquire_import_lock(target)
            require_empty_baseline(target)
            insert_all_tables_with_explicit_ids(source, target)
            validate_counts(source, target)
            validate_foreign_keys(target)
            reset_identity_sequences(target)
    return ImportReport(...)
```

Insert in dependency order: users, property/smart lists, searches, listings, runs, list items, notes, workflow, interactions, alerts, source runs, then listing versions. Adapt SQLite JSON text to JSONB and ISO timestamps to UTC. Validate every table count against a precomputed SQLite count; use catalog queries and anti-joins for PostgreSQL foreign-key validation. Test future inserts receive IDs above imported maxima.

- [ ] **Step 5: Implement explicit archive-only pruning**

Require `--archive-dir`; reject symlinks, directories, names outside the importer archive pattern, and files newer than 30 complete days. Prune only a matching archive plus matching manifest. The importer never invokes pruning and no command can take a source SQLite path as a deletion target.

- [ ] **Step 6: Run importer test suite**

Run: `POSTGRES_TEST_DSN='postgresql://immowbot_test:immowbot_test@127.0.0.1:55432/immowbot_test' python -m unittest tests.test_sqlite_importer -v`

Expected: PASS, including no-credential-output and rollback assertions.

- [ ] **Step 7: Commit**

```bash
git add src/buyer/sqlite_importer.py scripts/import_sqlite_to_postgres.py scripts/prune_sqlite_rollback_archives.py tests/sqlite_fixture.py tests/test_sqlite_importer.py
git commit -m "feat: add safe sqlite postgres importer"
```

### Task 6: Documentation and full verification

**Files:**
- Modify: `README.md`
- Modify: `docs/superpowers/specs/2026-09-16-sqlite-to-postgres-migration-design.md` only if implementation exposed a necessary design correction
- Create: `docs/postgres-migration.md`

**Interfaces:**
- Documents exact environment-variable names, migration command shapes, importer command shape, expected safe output, rollback procedure, and disposable test commands.
- Does not document, commit, or display production passwords, DSNs, certificate contents, or Pi secrets.

- [ ] **Step 1: Write documentation verification expectations**

```bash
rg -q 'DATABASE_MODE=local' README.md docs/postgres-migration.md
rg -q 'sslmode=verify-full' README.md docs/postgres-migration.md
rg -q -- '--sqlite-path' docs/postgres-migration.md
! rg -n 'postgresql://[^ ]*:[^ ]*@|IMMOTOOL_PASSWORD=' README.md docs/postgres-migration.md
```

- [ ] **Step 2: Add operator documentation**

Describe the required order: baseline migration on empty `immotool`, explicit archive/import dry validation, importer execution, local socket configuration, verification, and 30-day rollback retention. State explicitly that live Pi execution, secret provisioning, and source deletion require separate operator authorization.

- [ ] **Step 3: Run static SQL/dialect safety checks**

Run: `! rg -n 'sqlite3|PRAGMA|lastrowid|INSERT OR IGNORE|GROUP_CONCAT|json_extract|\?' src/buyer/property_store.py src/buyer/api.py src/buyer/dashboard.py src/buyer/scheduler.py`

Expected: success; intentional `?` user-interface strings are excluded by limiting the search to database call sites if needed.

- [ ] **Step 4: Run all tests using only disposable PostgreSQL**

Run: `docker compose -f docker-compose.test.yml up -d --wait && POSTGRES_TEST_DSN='postgresql://immowbot_test:immowbot_test@127.0.0.1:55432/immowbot_test' python -m unittest discover -s tests -v`

Expected: PASS. No test contacts `kodisrv` or requires a Pi.

- [ ] **Step 5: Validate image and Compose configuration without starting production services**

Run: `docker compose config --quiet && docker compose -f docker-compose-mac.yml config --quiet && docker compose -f docker-compose.test.yml config --quiet`

Expected: PASS; no credentials printed.

- [ ] **Step 6: Commit**

```bash
git add README.md docs/postgres-migration.md docs/superpowers/specs/2026-09-16-sqlite-to-postgres-migration-design.md
git commit -m "docs: document postgres migration workflow"
```
