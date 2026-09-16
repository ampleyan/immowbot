#!/bin/sh
set -e
REMOTE="/Volumes/ampleyan/projects/immowbot/data/buyer.db"
LOCAL="./data/buyer.db"

if [ ! -f "$REMOTE" ]; then
  echo "Remote not mounted. Connect to KODISRV first."
  exit 1
fi

mkdir -p ./data
cp "$REMOTE" "$LOCAL"
echo "Pulled prod DB to $LOCAL"
