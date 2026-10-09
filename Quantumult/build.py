#!/usr/bin/env python3
"""Build a QX profile by mirroring enabled functional dependencies.

Server subscriptions, credentials, certificates, icons and check URLs are not
mirrored. The build fails closed when too many dependencies cannot be mirrored,
so a half-broken profile is never published as a success.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

# The entry script lives at the package root; make `Quantumult.lib` importable
# however the file is invoked (python3 Quantumult/build.py, python3 -m ...).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Quantumult.lib.dependencies import (
    rewrite_profile, rewrite_resource, is_supported, is_rewritable)
from Quantumult.lib.section_inject import load_entries, inject_entries

ROOT = Path(__file__).resolve().parent
LOCAL_RULES = ROOT / "rewrite-local.txt"
LOCAL_POLICIES = ROOT / "policy-local.txt"
CACHE_FILE = ROOT / ".cache" / "upstream.json"
BASE_URL = "https://ddgksf2013.top/Profile/QuantumultX.conf"
REPO = os.environ.get("GITHUB_REPOSITORY", "Ethereal-09/rules-hub")
RAW = f"https://raw.githubusercontent.com/{REPO}/main/Quantumult/assets"
USER_AGENT = "Quantumult X/1.0.31"
SECTIONS = {"filter_remote": "filter", "rewrite_remote": "rewrite"}
MAX_BASE = 4 * 1024 * 1024
MAX_ASSET = 32 * 1024 * 1024

# Fail closed: a profile whose dependencies mostly point back at blocked upstreams
# is worse than no update at all, because the notification would claim success.
MAX_FAILED = int(os.environ.get("QX_MAX_FAILED", "8"))
MAX_FAILED_RATIO = float(os.environ.get("QX_MAX_FAILED_RATIO", "0.08"))

RETRY = 3
RETRY_BACKOFF = 2.0


# ---------------------------------------------------------------- HTTP helpers

def http_get(url, limit, extra_headers=None, retries=RETRY):
    """GET with bounded retries; returns (body, headers) or raises."""
    headers = {"User-Agent": USER_AGENT}
    if extra_headers:
        headers.update(extra_headers)
    last = None
    for attempt in range(1, retries + 1):
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=45) as response:
                body = response.read(limit + 1)
                if len(body) > limit:
                    raise ValueError("resource exceeds size limit")
                if not body:
                    raise ValueError("empty resource")
                return body, dict(response.headers)
        except urllib.error.HTTPError as exc:
            if exc.code in (304,):
                raise
            last = exc
            if exc.code in (408, 429, 500, 502, 503, 504) and attempt < retries:
                time.sleep(RETRY_BACKOFF * attempt)
                continue
            raise
        except Exception as exc:
            last = exc
            if attempt < retries:
                time.sleep(RETRY_BACKOFF * attempt)
                continue
            raise
    raise last if last else RuntimeError("download failed")


def download(url, limit, cache=None):
    """Download with ETag/Last-Modified revalidation when a cache entry exists."""
    headers = {}
    entry = cache.get(url) if cache else None
    if entry:
        if entry.get("etag"):
            headers["If-None-Match"] = entry["etag"]
        if entry.get("last_modified"):
            headers["If-Modified-Since"] = entry["last_modified"]
    try:
        body, resp = http_get(url, limit, headers)
    except urllib.error.HTTPError as exc:
        if exc.code == 304 and entry and "file" in entry:
            cached = ROOT / entry["file"]
            if cached.exists():
                return cached.read_bytes()
        raise
    if cache is not None:
        digest = hashlib.sha256(body).hexdigest()
        rel = f".cache/blob/{digest}"
        dest = ROOT / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists():
            dest.write_bytes(body)
        cache[url] = {
            "file": rel,
            "etag": resp.get("ETag", ""),
            "last_modified": resp.get("Last-Modified", ""),
        }
    return body


def load_cache():
    if not CACHE_FILE.exists():
        return {}
    try:
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_cache(cache):
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    temp = CACHE_FILE.with_name(CACHE_FILE.name + ".tmp")
    temp.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    os.replace(temp, CACHE_FILE)


def safe_public_url(url):
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
        return False
    if parts.fragment:
        return False
    if re.search(r"(?:token|key|auth|secret|password|subscribe|subscription)", parts.path, re.I):
        return False
    if re.search(r"(?:token|key|auth|secret|password)", parts.query, re.I):
        return False
    # Harmless presentation parameters used by raw file hosts.
    if parts.query and not re.fullmatch(r"(?:[\w.~-]+=[\w.~%-]*&?)+", parts.query, re.I):
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


def replace_preamble(text):
    """Replace upstream's lengthy header, never modify QX configuration sections."""
    match = re.search(r"(?im)^\[general\][ \t]*(?:\r?\n|$)", text)
    if not match:
        raise ValueError("base is not a Quantumult X profile: missing [general]")
    original_header = text[:match.start()]
    if any(line.strip() and not line.lstrip().startswith(("#", ";", "//"))
           for line in original_header.splitlines()):
        raise ValueError("unexpected active content before [general]; refusing to discard it")
    header = (
        "# Quantumult X 配置 · Ethereal-09 / rules-hub\n"
        "# 来源底包：https://ddgksf2013.top/Profile/QuantumultX.conf\n"
        "# 原底包作者：@ddgksf2013；规则与脚本版权归各上游作者。\n"
        f"# 项目：https://github.com/{REPO}\n"
        f"# 配置订阅：https://raw.githubusercontent.com/{REPO}/main/Quantumult/dist/QuantumultX.conf\n"
        "# 本仓库每日构建：保留底包功能配置，仅镜像已启用且可安全下载的功能资源。\n"
        "# 资源来源与 SHA-256：见 Quantumult/SOURCES.md；失败项保留原链接。\n"
        "# 导入前请备份现有 QX 配置；节点订阅、证书与图标不会镜像。\n\n"
    )
    return header + text[match.start():]


def process(text, fetch, assets, sources=None, local_rules=None, local_policies=None,
            failures=None):
    if sources is None:
        sources = {}
    if failures is None:
        failures = []
    local_rules = local_rules or []
    local_policies = local_policies or []
    if not re.search(r"(?im)^\s*\[general\]\s*$", text):
        raise ValueError("base is not a Quantumult X profile: missing [general]")
    # Personal policies and rewrites are injected before any URL is mirrored,
    # so their script URLs take the exact same mirroring path as upstream rules.
    text = inject_entries(text, "rewrite_remote", local_rules, "个人追加")
    text = inject_entries(text, "policy", local_policies, "个人追加策略组")
    lines = text.splitlines(keepends=True)
    section = ""
    count = {"filter": 0, "rewrite": 0, "script": 0, "failed": 0, "skipped": 0}
    result = []
    pending = set()

    def mirror(url, category="script"):
        if not safe_public_url(url) or (category == "script" and not is_supported(url)):
            count["skipped"] += 1
            return url
        relative = f"{category}/{mirror_name(url)}"
        new_url = f"{RAW}/{relative}"
        if relative in pending:
            # The same resource is already being fetched higher up the stack.
            # Reuse the URL we are going to publish instead of recursing forever.
            return new_url
        if relative not in assets:
            pending.add(relative)
            try:
                blob = fetch(url, MAX_ASSET)
                sample = blob[:512].lstrip().lower()
                if sample.startswith((b"<!doctype html", b"<html")) or b"\x00" in blob:
                    raise ValueError("not a text rule resource")
                # Only configuration text is parsed for nested dependencies. A JS
                # payload is opaque code; rewriting it corrupts the script.
                if is_rewritable(url):
                    decoded = blob.decode("utf-8-sig")
                    blob = rewrite_resource(decoded, lambda dependency: attempt(dependency)).encode("utf-8")
                assets[relative] = blob
                sources[relative] = (url, hashlib.sha256(blob).hexdigest())
            finally:
                pending.remove(relative)
        count[category] += 1
        return new_url

    def attempt(url, category="script"):
        try:
            return mirror(url, category)
        except Exception as exc:
            count["failed"] += 1
            detail = f"{category}\t{url}\t{type(exc).__name__}: {exc}"
            failures.append(detail)
            print(f"WARN: mirror failed ({type(exc).__name__}: {exc}); original URL retained [{url}]",
                  file=sys.stderr)
            return url

    for line in lines:
        m = re.match(r"^\s*\[([^\]]+)\]\s*(?:\r?\n)?$", line)
        if m:
            section = m.group(1).lower()
        category = SECTIONS.get(section)
        if not category or not line.strip() or line.lstrip().startswith(("#", ";", "//")):
            result.append(line)
            continue
        ending = "\r\n" if line.endswith("\r\n") else "\n" if line.endswith("\n") else ""
        m = re.match(r"^([^\S\r\n]*)(https?://[^\s,]+)([^\r\n]*)$", line[:-len(ending)] if ending else line)
        if not m or re.search(r"(?:^|,)\s*enabled\s*=\s*false\b", m.group(3), re.I):
            result.append(line)
            continue
        prefix, url, rest = m.groups()
        result.append(f"{prefix}{attempt(url, category)}{rest}{ending}")
    output = rewrite_profile("".join(result), attempt)
    return replace_preamble(output), count


def check_failure_budget(stats):
    """Refuse to publish when too many dependencies could not be mirrored."""
    failed = stats["failed"]
    total = failed + stats["filter"] + stats["rewrite"] + stats["script"]
    if failed <= MAX_FAILED:
        return
    ratio = (failed / total) if total else 1.0
    if ratio > MAX_FAILED_RATIO:
        raise ValueError(
            f"镜像失败 {failed}/{total}（{ratio:.1%}），超过阈值"
            f"（最多 {MAX_FAILED} 个且不超过 {MAX_FAILED_RATIO:.0%}）；拒绝发布半成品配置")


def make_sources_md(sources, stats, failures):
    """Stable, readable inventory; never list credential-bearing URLs."""
    lines = [
        "# Quantumult X 镜像来源", "",
        "自动生成；仅记录本次成功镜像且被当前配置引用的功能文件。",
        "旧文件为兼容客户端缓存会保留在 assets/，不代表仍处于启用状态。", "",
        f"本次：分流 {stats['filter']}、重写 {stats['rewrite']}、脚本引用 {stats['script']}；"
        f"失败 {stats['failed']}、跳过 {stats['skipped']}。", "",
    ]
    if failures:
        lines += ["## 未能镜像（保留上游原链接）", "",
                  "以下条目仍指向上游地址；若上游不可达，客户端侧不会生效。", ""]
        lines += [f"- `{item.split(chr(9))[1]}` — {item.split(chr(9))[2]}" for item in failures]
        lines.append("")
    lines += ["## 成功镜像", "", "| 本仓库文件 | 原始地址 | SHA-256 |", "|---|---|---|"]
    for relative, (url, digest) in sorted(sources.items()):
        path = f"assets/{relative}"
        lines.append(f"| [`{path}`]({path}) | `{url}` | `{digest}` |")
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-file", type=Path, help="offline fixture; otherwise fetch upstream")
    parser.add_argument("--output", type=Path, default=ROOT / "dist" / "QuantumultX.conf")
    parser.add_argument("--no-cache", action="store_true", help="ignore the on-disk HTTP cache")
    args = parser.parse_args()

    cache = {} if args.no_cache else load_cache()
    if args.base_file:
        base = args.base_file.read_bytes()
    else:
        base = download(BASE_URL, MAX_BASE, cache)
    if len(base) > MAX_BASE or not base.strip():
        raise ValueError("base missing or too large")
    text = base.decode("utf-8-sig")

    assets = {}
    sources = {}
    failures = []
    local_rules = load_entries(LOCAL_RULES)
    if local_rules:
        print(f"Pers: 追加重写 {len(local_rules)} 条（rewrite-local.txt）")
    local_policies = load_entries(LOCAL_POLICIES)
    if local_policies:
        print(f"Pers: 追加策略组 {len(local_policies)} 条（policy-local.txt）")

    output, stats = process(text, lambda url, limit: download(url, limit, cache),
                            assets, sources, local_rules, local_policies, failures)

    # Fail closed before touching any output file.
    check_failure_budget(stats)

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
    manifest = ROOT / "SOURCES.md"
    manifest_temp = manifest.with_name(manifest.name + ".tmp")
    manifest_temp.write_text(make_sources_md(sources, stats, failures), encoding="utf-8")
    os.replace(manifest_temp, manifest)
    if not args.no_cache:
        save_cache(cache)
    print(f"Built {args.output}: {stats}, stored assets: {len(assets)}")
    if failures:
        print(f"WARNING: {len(failures)} dependency/ies retained upstream URL; "
              f"see SOURCES.md 未能镜像 section", file=sys.stderr)


if __name__ == "__main__":
    main()
