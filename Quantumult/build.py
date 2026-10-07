#!/usr/bin/env python3
"""Build a QX profile by mirroring only enabled remote filters and rewrites.

No server subscription, certificate or script URL is mirrored. URLs containing
credentials/query strings are deliberately left untouched in the public output.
"""
import argparse
import hashlib
import os
from pathlib import Path
import re
import sys
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parent
BASE_URL = "https://ddgksf2013.top/Profile/QuantumultX.conf"
REPO = os.environ.get("GITHUB_REPOSITORY", "Ethereal-09/rules-hub")
RAW = f"https://raw.githubusercontent.com/{REPO}/main/Quantumult/assets"
USER_AGENT = "Quantumult X/1.0.31"
SECTIONS = {"filter_remote": "filter", "rewrite_remote": "rewrite"}
MAX_BASE = 4 * 1024 * 1024
MAX_ASSET = 32 * 1024 * 1024


def download(url, limit):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=45) as response:
        if response.status != 200:
            raise ValueError("HTTP status not 200")
        data = response.read(limit + 1)
        if len(data) > limit:
            raise ValueError("resource exceeds size limit")
        if not data:
            raise ValueError("empty resource")
        return data


def safe_public_url(url):
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
        return False
    if parts.query or parts.fragment or re.search(r"(?:token|key|auth|secret|password|subscribe|subscription)", parts.path, re.I):
        return False
    return True


def mirror_name(url):
    parts = urllib.parse.urlsplit(url)
    suffix = Path(parts.path).suffix.lower()
    if not re.fullmatch(r"\.[a-z0-9]{1,10}", suffix):
        suffix = ".txt"
    stem = re.sub(r"[^a-zA-Z0-9_-]", "-", Path(parts.path).stem)[:50] or "resource"
    digest = hashlib.sha256(url.encode()).hexdigest()[:16]
    return f"{stem}-{digest}{suffix}"


def process(text, fetch, assets):
    if not re.search(r"(?im)^\s*\[general\]\s*$", text):
        raise ValueError("base is not a Quantumult X profile: missing [general]")
    lines = text.splitlines(keepends=True)
    section = ""
    count = {"filter": 0, "rewrite": 0, "failed": 0, "skipped": 0}
    result = []
    for line in lines:
        m = re.match(r"^\s*\[([^\]]+)\]\s*(?:\r?\n)?$", line)
        if m:
            section = m.group(1).lower()
        category = SECTIONS.get(section)
        # Preserve blank lines, comments and disabled resources byte-for-byte.
        if not category or not line.strip() or line.lstrip().startswith(("#", ";", "//")):
            result.append(line)
            continue
        # Regex '.' excludes the line ending; explicitly preserve it when
        # replacing a URL or consecutive subscriptions merge into one line.
        ending = "\r\n" if line.endswith("\r\n") else "\n" if line.endswith("\n") else ""
        m = re.match(r"^([^\S\r\n]*)(https?://[^\s,]+)([^\r\n]*)$", line[:-len(ending)] if ending else line)
        if not m or re.search(r"(?:^|,)\s*enabled\s*=\s*false\b", m.group(3), re.I):
            result.append(line)
            continue
        prefix, url, rest = m.groups()
        if not safe_public_url(url):
            count["skipped"] += 1
            result.append(line)
            continue
        relative = f"{category}/{mirror_name(url)}"
        try:
            if relative not in assets:
                blob = fetch(url, MAX_ASSET)
                # Reject HTML error pages; QX remote resources are text.
                sample = blob[:512].lstrip().lower()
                if sample.startswith((b"<!doctype html", b"<html")) or b"\x00" in blob:
                    raise ValueError("not a text rule resource")
                assets[relative] = blob
            count[category] += 1
            result.append(f"{prefix}{RAW}/{relative}{rest}{ending}")
        except Exception as exc:
            count["failed"] += 1
            print(f"WARN: {category} resource download failed ({type(exc).__name__}); original URL retained", file=sys.stderr)
            result.append(line)
    return "".join(result), count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-file", type=Path, help="offline fixture; otherwise fetch upstream")
    parser.add_argument("--output", type=Path, default=ROOT / "dist" / "QuantumultX.conf")
    args = parser.parse_args()
    if args.base_file:
        base = args.base_file.read_bytes()
    else:
        base = download(BASE_URL, MAX_BASE)
    if len(base) > MAX_BASE or not base.strip():
        raise ValueError("base missing or too large")
    text = base.decode("utf-8-sig")
    assets = {}
    output, stats = process(text, download, assets)
    # Only write the new profile after the base is valid and every successful
    # resource has been staged. Old assets stay available for old QX imports.
    for relative, blob in assets.items():
        dest = ROOT / "assets" / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        temp = dest.with_name(dest.name + ".tmp")
        temp.write_bytes(blob)
        os.replace(temp, dest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temp = args.output.with_name(args.output.name + ".tmp")
    temp.write_text(output, encoding="utf-8")
    os.replace(temp, args.output)
    print(f"Built {args.output}: {stats}, stored assets: {len(assets)}")
    if stats["failed"]:
        print("WARNING: some upstream URLs were retained; see warnings above", file=sys.stderr)


if __name__ == "__main__":
    main()
