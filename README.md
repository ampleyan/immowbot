# Immowbot

A self-hosted Belgian real estate tracker. Scrapes Immoweb, Immoscoop, Zimmo, Realo, and Immovlan, scores listings against your search criteria, translates Dutch descriptions to English, and tracks price changes over time.

**Current version:** see `VERSION` file — displayed in the sidebar after deployment.

---

## Quick start (Docker)

```bash
# Clone and start
git clone <repo>
cd immowbot
docker compose up --build -d
```

Open `http://localhost:8000`. The database uses PostgreSQL (local Unix socket or remote via `kodisrv`).

### Mac (local Ollama)

If you already have Ollama running on your Mac:

```bash
docker compose -f docker-compose-mac.yml up --build -d
```

This skips the Docker Ollama service and connects to `host.docker.internal:11434` instead.

### Raspberry Pi / server

```bash
git pull
APP_VERSION=$(cat VERSION) docker compose up --build -d
```

For a lighter translation model on low-RAM devices:

```bash
OLLAMA_MODEL=qwen2.5:0.5b APP_VERSION=$(cat VERSION) docker compose up --build -d
```

| Model | RAM | Quality |
|-------|-----|---------|
| `qwen2.5:0.5b` | ~400 MB | Basic, fast |
| `qwen2.5:1.5b` (default) | ~1 GB | Good balance |

---

## Database

Immowbot uses PostgreSQL. For migration from SQLite, setup procedures, and rollback instructions, see [PostgreSQL Migration Guide](docs/postgres-migration.md).

### Windows local development

The Windows profile starts PostgreSQL, creates the database on the first run, applies pending migrations, and connects to Ollama running on the Windows host:

```powershell
$env:IMMOWBOT_INVITE_TOKEN = "<invite-token>"
$env:IMMOWBOT_AUTH_SECRET = "<auth-secret>"
docker compose -f docker-compose.windows.yml up --build -d
```

Migrations run on every start and are tracked in `schema_migrations`, so already-applied migrations are skipped.

### Remote database

The remote profile starts only the app. It does not start PostgreSQL or run migrations. The remote database must already exist and be reachable using the DSN rules in [PostgreSQL Migration Guide](docs/postgres-migration.md). Ollama still defaults to the Windows host; override `OLLAMA_BASE_URL` when using a remote Ollama service.

Place the CA certificate at `certs/kodisrv-ca.crt`, and set `DATABASE_DSN` to reference `/run/immowbot/certs/kodisrv-ca.crt` inside the container:

```powershell
$env:IMMOWBOT_INVITE_TOKEN = "<invite-token>"
$env:IMMOWBOT_AUTH_SECRET = "<auth-secret>"
$env:DATABASE_DSN = "host=kodisrv dbname=immotool user=immotool password=<password> sslmode=verify-full sslrootcert=/run/immowbot/certs/kodisrv-ca.crt"
docker compose -f docker-compose.remote.yml up --build -d
```

---

## Deploying updates

```bash
./bump.sh                          # increments minor version, commits, pushes
ssh pi@kodi "cd ~/immowbot && git pull && APP_VERSION=$(cat VERSION) docker compose up --build -d"
```

---

## Interface guide

### Sidebar (left panel)

The sidebar is always visible and contains all configuration.

**Search config** — defines what counts as a match:
- Postcodes, max price, min surface, min bedrooms
- Outdoor features (terrace / garden) as hard requirements
- Building age filter (any / new project / existing)
- Construction year range
- Scraping mode: **All listings** re-scrapes everything; **Delta** only fetches new listings (capped at 3 pages)
- Score importance weights — five sliders that must total 100%
- EPC labels — only listings with these labels pass the hard filter
- Portals — which sources to scrape
- Pages per portal

**Purchase feasibility** — your financial parameters used to estimate whether a listing is affordable: capital, income, existing debts, interest rate, loan term, LTV.

**Commute destinations** — JSON array of destinations with coordinates and max travel time. Shown on each listing card.

**Collection** — start or cancel a scrape run. Live progress shows checked/saved counts and current portal. During translation, a purple progress bar shows how many descriptions have been translated.

**Account** — change password, sign out.

**Version** — shown at the bottom (e.g. `v1.1.0`).

---

### Active tab

The main listings view. Shows all listings that passed the hard filters, sorted by score.

**Triage system** — listings start in **Pending**. Move them through statuses:
- `Interested` → `Contacted` → `Visit planned` → `Offer` → `Rejected`

Each status has its own count and filter. The **Pending** view has a triage sub-filter: All / New / Changed / Follow-ups.

**Filters (WHERE panel)**

| Filter | Description |
|--------|-------------|
| Portal | Immoweb, Zimmo, Immoscoop, etc. |
| Postcode | One or more postcodes |
| EPC | Filter by energy label |
| Potential benefits | Tax breaks, renovation grants, etc. |
| Bedrooms | Minimum |
| Surface area | Min / max m² |
| Price | Min / max € |
| Score | Min / max score |
| Construction year | Min / max year |
| Max monthly charges | Common charges cap (€/month) |
| Terrace or garden | Has outdoor space |
| Has parking / garage | Parking confirmed in listing data |
| Owner-occupied (no tenant) | Excludes properties with tenants |
| Without picture | Fewer than 3 photos |
| Has description | Has a text description |
| Dutch only | Has description but no English translation yet |

**Toolbar**
- Select / deselect all visible listings
- Delete selected
- Rescrape selected (re-fetches full details for selected listings)
- Translate selected — runs translation on selected listings; progress shown in sidebar
- Sort: score, price, surface, date

**Property cards**

Each card shows:
- Photo with **score circle** overlaid top-right (green ≥ 80, yellow 60–79, red < 60)
- Price, property type, address
- Specs: bedrooms · m² · floor · postcode
- Score component highlights (top contributors)
- Badges: EPC, source portal, new, excluded, under option, ↓ price reduced, tenant in place, €X/mo charges, 🅿 parking, outdoor features, saved, note

Click a card to open the **Detail Panel** inline below it (or navigate with arrow keys). The panel shows:
- Full photo gallery
- Translated English description
- Score breakdown
- Pipeline actions (status, notes, follow-up dates)
- Purchase estimate
- Commute times
- Price history
- Map

---

### Alerts tab

Shows listings that are new matches since the last time you cleared alerts — i.e. listings that appeared in the DB after your search criteria were met. Badge count shown on the tab.

Click a card to open its Detail Panel. **Clear all** marks all current alerts as read; cleared alerts never reappear.

---

### Lists tab

Save listings to named lists (e.g. "Shortlist", "To visit"). A listing can be in multiple lists.

---

### Pipeline tab

Kanban-style view across all workflow statuses. Useful for tracking your active search process.

---

### Dupe tab

Shows groups of listings that appear to be the same property across different portals. Merge duplicates to keep the richer record and discard the other.

---

### History tab

All past collection runs with source breakdown (checked / saved per portal) and timestamps.

---

## How scoring works

Every listing must first pass the **hard filters**: correct postcode, property type, price ≤ max, surface ≥ min, bedrooms ≥ min, EPC in allowed labels, construction year in range (if set), tenant excluded (if configured). Listings that fail are shown as "excluded" with a grey score.

Passing listings receive a score built from:

**Base components (configurable weights, must total 100):**

| Component | Default weight | Logic |
|-----------|---------------|-------|
| Price | 30 | Headroom below max price |
| Surface area | 25 | How far above minimum |
| Bedrooms | 15 | How far above minimum |
| EPC | 20 | A++/A+/A = full, G = 0 |
| Completeness | 10 | Fraction of key fields present |

**Bonus/penalty components (added on top, score capped at 100):**

| Component | Points | Trigger |
|-----------|--------|---------|
| Outdoor | +5 | Has terrace, garden, or outdoor surface |
| Parking | +5 | Garage or parking confirmed |
| Price per m² | +0–10 | Linear: how far below postcode average €/m² |
| Price reduced | +5 | Any prior version had a higher price |
| Days on market | +5 / −5 | Fresh (<14 days) = +5; stale (>90 days) = −5 |
| Tenant in place | −10 | Property has current tenant |
| Monthly charges | 0 to −10 | Linear penalty above €150/month |

---

## Data backups

After every collection run, a full snapshot of all listings is written to `data/backups/YYYY-MM-DD_HH-MM-SS_run-{id}.json`. Use these to compare which fields were available at different points in time:

```bash
python3 -c "
import json
a = json.load(open('data/backups/2026-09-14_run-3.json'))
b = json.load(open('data/backups/2026-09-15_run-4.json'))
keys_a = set(k for l in a for k in l)
keys_b = set(k for l in b for k in l)
print('New fields:', keys_b - keys_a)
"
```

---

## What's new (v1.1.0)

- **Alerts tab** — new tab showing unread listing matches as scored property cards with inline detail panel
- **Translation progress** — purple bar in sidebar shows translation progress during scraping and manual translate
- **Translate selected** — button in toolbar translates only selected listings on demand
- **Score overlay** — score shown as a circle on the listing photo instead of a text pill
- **New score bonuses** — parking, price/m² vs postcode average, price reduction, days on market
- **New score penalties** — tenant in place (−10), high monthly charges (up to −10)
- **New filters** — score range, price range, construction year, max monthly charges, has parking, owner-occupied
- **Property card badges** — price reduced, tenant in place, monthly charges, parking shown as pills
- **Floor** shown in card specs line
- **Delta scraping cap** — delta mode limited to 3 pages to avoid excessive scraping
- **JSON backups** — full listing snapshot saved after each run to `data/backups/`
- **Versioning** — `VERSION` file + `bump.sh` + version shown in sidebar

---

## Translations

Translations use a local Ollama model — no API key required. The translator only runs on listings with Dutch descriptions that have not been translated yet.

On Docker deployments, Ollama starts automatically and pulls the model on first boot. On Mac with local Ollama, use `docker-compose-mac.yml` which connects to your host Ollama.

If Ollama is unavailable, the original description is kept and no error is raised.

---

## Run tests

```bash
python -m pytest tests/ -v
```
