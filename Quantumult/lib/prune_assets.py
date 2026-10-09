#!/usr/bin/env python3
"""Prune mirrored assets that are no longer referenced by recent profiles.

A file is kept when it is referenced by the current build or was modified within
the retention window. This bounds repository growth without breaking clients that
still hold an older profile.
"""
import argparse
import os
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[1]   # Quantumult/
ASSETS = ROOT / "assets"
DEFAULT_DAYS = 30
ASSET_REF = re.compile(r"Quantumult/assets/(?:filter|rewrite|script)/([^\s,)\"']+)")


def referenced_by(path):
    """Return asset paths referenced by a profile/SOURCES file, if it exists."""
    if not path.exists():
        return set()
    text = path.read_text(encoding="utf-8", errors="replace")
    return set(ASSET_REF.findall(text))


def prune(days, dry_run=False):
    if not ASSETS.exists():
        print("assets/ 不存在，跳过清理")
        return 0, 0
    keep = referenced_by(ROOT / "dist" / "QuantumultX.conf")
    keep |= referenced_by(ROOT / "SOURCES.md")
    cutoff = time.time() - days * 86400

    removed = kept = 0
    for category in ("filter", "rewrite", "script"):
        folder = ASSETS / category
        if not folder.is_dir():
            continue
        for f in sorted(folder.iterdir()):
            if not f.is_file():
                continue
            rel = f"{category}/{f.name}"
            if rel in keep or f.stat().st_mtime >= cutoff:
                kept += 1
                continue
            if dry_run:
                print(f"  would remove: assets/{rel}")
            else:
                f.unlink()
                print(f"  removed: assets/{rel}")
            removed += 1
    return removed, kept


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=DEFAULT_DAYS,
                        help=f"retention window in days (default {DEFAULT_DAYS})")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    removed, kept = prune(args.days, args.dry_run)
    print(f"清理完成：移除 {removed}，保留 {kept}（保留窗口 {args.days} 天）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
