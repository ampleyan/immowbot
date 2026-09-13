# ── Stage 1: build Vue frontend ────────────────────────────────────────────
FROM node:22-alpine AS ui
WORKDIR /build
COPY frontend/package*.json ./
RUN npm install --legacy-peer-deps --silent
COPY frontend/ ./
RUN npm run build-only

# ── Stage 2: Python app + Chrome ───────────────────────────────────────────
FROM python:3.12-slim

# Chrome is required for Selenium-based scraping
RUN apt-get update && apt-get install -y --no-install-recommends \
        wget gnupg ca-certificates \
    && wget -qO /tmp/gc.key https://dl.google.com/linux/linux_signing_key.pub \
    && apt-key add /tmp/gc.key \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" \
       > /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update && apt-get install -y --no-install-recommends \
        google-chrome-stable \
    && rm -rf /var/lib/apt/lists/* /tmp/gc.key

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY --from=ui /build/dist ./frontend/dist

RUN mkdir -p data

ENV PYTHONUNBUFFERED=1
ENV CHROME_BIN=/usr/bin/google-chrome

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "src.buyer.api:app", "--host", "0.0.0.0", "--port", "8000"]
