#!/bin/sh
set -e
REMOTE="/Volumes/ampleyan/projects/immowbot/data/buyer.db"
LOCAL="./data/buyer.db"

if [ ! -f "$REMOTE" ]; then
  echo "Remote not mounted. Connect to KODISRV first."
  exit 1
fi

if [ ! -f "$LOCAL" ]; then
  echo "No local DB found at $LOCAL"
  exit 1
fi

echo "WARNING: This overwrites the prod DB on KODISRV."
printf "Continue? [y/N] "
read answer
[ "$answer" = "y" ] || [ "$answer" = "Y" ] || { echo "Aborted."; exit 1; }

cp "$LOCAL" "$REMOTE"
echo "Pushed local DB to prod."
