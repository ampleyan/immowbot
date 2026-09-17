# ── Stage 1: build Vue frontend ────────────────────────────────────────────
FROM node:22-alpine AS ui
WORKDIR /build
COPY frontend/package*.json ./
RUN npm install --legacy-peer-deps --silent
COPY frontend/ ./
RUN npm run build-only

# ── Stage 2: Python app + Chrome ───────────────────────────────────────────
FROM python:3.12-slim

# Chromium is required for Selenium-based scraping and supports amd64/arm64
RUN apt-get update && apt-get install -y --no-install-recommends \
        chromium chromium-driver \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ARG APP_VERSION=dev
ENV APP_VERSION=$APP_VERSION

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY VERSION ./
COPY migrations/ ./migrations/
COPY src/ ./src/
COPY --from=ui /build/dist ./frontend/dist

RUN mkdir -p data

ENV PYTHONUNBUFFERED=1
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROMEDRIVER_BIN=/usr/bin/chromedriver

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "src.buyer.api:app", "--host", "0.0.0.0", "--port", "8000"]
