# Launching Immowbot

## Mac / Windows (local dev)

### Prerequisites
- Docker Desktop
- Git
- KODISRV reachable on your LAN (`192.168.129.39`)

### 1. Clone
```bash
git clone git@github.com:ampleyan/immowbot.git
cd immowbot
```

### 2. Create `.env`
```
IMMOWBOT_INVITE_TOKEN=ikookalstiblijft
IMMOWBOT_AUTH_SECRET=ikookalstiblijft
OLLAMA_MODEL=qwen2.5:0.5b
DATABASE_MODE=local
DATABASE_DSN=host=192.168.129.39 dbname=immotool user=immotool password=<IMMOTOOL_PASSWORD>
TRUSTED_IPS=127.0.0.1,::1,192.168.1.42
```

> `DATABASE_DSN` uses the KODISRV LAN IP directly — this works from Mac/Windows Docker because
> Docker Desktop routes host-network traffic through the host machine.

### 3. Launch
```bash
docker-compose -f docker-compose-mac.yml up --build
```

### 4. Open
http://localhost:666

---

## KODISRV (production)

Production runs via `docker-compose.yml` (not the mac variant).
It connects to the shared `postgres-postgres-1` container on the same host.

### Prerequisites on KODISRV
- `postgres-postgres-1` container running (from `~/projects/rpi-postgresql`)
- `pg_hba.conf` must allow `172.16.0.0/12` (Docker bridge networks) — already committed to `rpi-postgresql` repo

### `.env` on KODISRV (`~/projects/immowbot/.env`)
```
IMMOWBOT_INVITE_TOKEN=ikookalstiblijft
IMMOWBOT_AUTH_SECRET=ikookalstiblijft
OLLAMA_MODEL=qwen2.5:0.5b
OLLAMA_BASE_URL=http://<WINDOWS_IP>:11434
DATABASE_MODE=local
DATABASE_DSN=host=172.20.0.2 dbname=immotool user=immotool password=<IMMOTOOL_PASSWORD>
TRUSTED_IPS=127.0.0.1,::1,169.224.189.199
```

> `DATABASE_DSN` uses the postgres container's internal Docker IP (`172.20.0.2`), not the LAN IP.
> The LAN IP (`192.168.129.39`) is not routable from inside Docker bridge networks on Linux.
> If you ever recreate the postgres container, verify its IP with:
> `docker network inspect postgres_default`

> `OLLAMA_BASE_URL` points to the Windows machine running Ollama.
> On Windows, set `OLLAMA_HOST=0.0.0.0` permanently and allow port 11434 through the firewall.

### Deploy / update
```bash
ssh ampleyan@kodisrv
cd ~/projects/immowbot
git pull
docker compose up -d --build
```

### Networking setup (already done, recorded here for rebuild)
`docker-compose.yml` attaches the app to `postgres_default` (external network from `rpi-postgresql`).
This allows the app container to reach postgres by its internal IP.
No manual `docker network connect` needed — it's in the compose file.
