#!/usr/bin/env python3
"""Delete rollback archives older than 30 complete days."""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

# Allow running from the repo root
sys.path.insert(0, str(Path(__file__).parents[1]))

from src.buyer.sqlite_importer import prune_expired_archives


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Delete Immowbot rollback archives older than 30 complete days."
            " Only deletes files matching the archive pattern; never touches"
            " SQLite source files."
        )
    )
    parser.add_argument(
        "--archive-dir",
        required=True,
        help="Absolute path to the rollback archive directory",
    )
    args = parser.parse_args()

    archive_dir = Path(args.archive_dir)
    now = datetime.now(timezone.utc)

    try:
        deleted = prune_expired_archives(archive_dir, now)
    except ValueError as exc:
        print(f"prune failed: {exc}", file=sys.stderr)
        return 1

    if deleted:
        print(f"deleted {len(deleted)} file(s):")
        for path in deleted:
            print(f"  {path.name}")
    else:
        print("no archives eligible for deletion")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
