# Launching Immowbot

## Prerequisites

- Docker Desktop (Mac, Windows with WSL2, or Linux)
- Git
- KODISRV reachable at `192.168.129.39` on your local network

## Setup

### 1. Clone

```bash
git clone git@github.com:ampleyan/immowbot.git
cd immowbot
```

### 2. Create `.env` in the project root

```
IMMOWBOT_INVITE_TOKEN=ikookalstiblijft
IMMOWBOT_AUTH_SECRET=ikookalstiblijft
OLLAMA_MODEL=qwen2.5:0.5b
DATABASE_MODE=local
DATABASE_DSN=host=192.168.129.39 dbname=immotool user=immotool password=<IMMOTOOL_PASSWORD>
TRUSTED_IPS=127.0.0.1,::1,192.168.1.42
```

### 3. Launch

```bash
docker-compose -f docker-compose-mac.yml up --build
```

### 4. Open

http://localhost:666

---

## Notes

- Connects to the shared PostgreSQL on KODISRV via TCP — no local database needed.
- On first start, Ollama pulls the model inside the container (takes a few minutes).
- Login with the invite token set in `IMMOWBOT_INVITE_TOKEN`.
- `docker-compose-mac.yml` works on Mac, Windows, and Linux for local dev.

## KODISRV (production)

The production instance runs on KODISRV at port 8000 via `docker-compose.yml`.
It connects to the same PostgreSQL database (`immotool` on `postgres-postgres-1`).

To restart production after a code update:

```bash
ssh kodisrv
cd ~/projects/immowbot
git pull
docker-compose up -d --build
```
