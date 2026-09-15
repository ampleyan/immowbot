#!/bin/sh
set -e
current=$(cat VERSION | tr -d '[:space:]')
major=$(echo "$current" | cut -d. -f1)
minor=$(echo "$current" | cut -d. -f2)
patch=$(echo "$current" | cut -d. -f3)
new="$major.$((minor + 1)).$patch"
echo "$new" > VERSION
echo "Version: $current → $new"
git add VERSION
git commit -m "chore: bump version to $new"
git push
