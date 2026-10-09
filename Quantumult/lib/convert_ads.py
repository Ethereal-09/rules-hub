#!/usr/bin/env python3
"""Conservatively derive QX ad-domain rules from merged AdGuard outputs.

Only plain domain anchors are converted. Exceptions suppress the same domain
and its subdomains; ambiguous whitelist syntax is reported, never guessed.
"""
from collections import Counter
from pathlib import Path
import argparse
import re
import urllib.request

SOURCE_FILE = Path(__file__).with_name("ads-sources.txt")
SOURCE_MAX_BYTES = 20 * 1024 * 1024
QX_SUFFIX = re.compile(r"^host-suffix\s*,\s*(" + r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z](?:[a-z0-9-]{0,61}[a-z0-9])?" + r")\s*,\s*reject$", re.I)

ROOT = Path(__file__).resolve().parents[2]   # 仓库根（lib/ → Quantumult/ → repo）
DOMAIN = r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z](?:[a-z0-9-]{0,61}[a-z0-9])?"
PLAIN = re.compile(r"^\|\|(" + DOMAIN + r")\^$", re.I)
IMPORTANT = re.compile(r"^\|\|(" + DOMAIN + r")\^\$important$", re.I)
BARE = re.compile(r"^(" + DOMAIN + r")$", re.I)


def parse_domain(line):
    """Return domain only for a precisely representable domain-suffix rule."""
    match = PLAIN.fullmatch(line) or BARE.fullmatch(line)
    return match.group(1).lower() if match else None


def convert(black, white):
    stats = Counter()
    allow = set()
    for raw in white.splitlines():
        line = raw.strip().lower()
        if not line or line.startswith(("!", "#", "[")):
            continue
        stats["white_input"] += 1
        if not line.startswith("@@"):
            stats["white_non_exception"] += 1
            continue
        domain = parse_domain(line[2:])
        if domain:
            allow.add(domain)
        else:
            stats["white_ambiguous"] += 1
    blocked = set()
    for raw in black.splitlines():
        line = raw.strip().lower()
        if not line or line.startswith(("!", "#", "[")):
            continue
        stats["black_input"] += 1
        if line.startswith("@@"):
            domain = parse_domain(line[2:])
            if domain:
                allow.add(domain)
            else:
                stats["white_ambiguous"] += 1
            continue
        important = IMPORTANT.fullmatch(line)
        domain = important.group(1).lower() if important else parse_domain(line)
        if important:
            stats["important_downgraded"] += 1
        if not domain:
            stats["black_unsupported"] += 1
        else:
            blocked.add(domain)
    # Exception to a parent domain also excludes all child-domain rejects.
    kept = []
    for domain in sorted(blocked):
        labels = domain.split(".")
        if any(".".join(labels[i:]) in allow for i in range(len(labels) - 1)):
            stats["excluded"] += 1
        else:
            kept.append(f"HOST-SUFFIX,{domain},REJECT")
    stats["converted"] = len(kept)
    stats["unique_black"] = len(blocked)
    stats["unique_allow"] = len(allow)
    return kept, stats


def merge_qx_sources(rules, sources, fetch):
    """Keep only QX HOST-SUFFIX reject rules; dedupe against AdGuard output."""
    merged = {r.lower(): r for r in rules}
    stats = Counter()
    for url in sources:
        raw = fetch(url)
        if not raw or len(raw) > SOURCE_MAX_BYTES:
            raise ValueError("QX 上游为空或超出大小限制")
        seen = 0
        for original in raw.decode("utf-8-sig").splitlines():
            line = original.strip()
            if not line or line.startswith(("#", "!", ";")):
                continue
            match = QX_SUFFIX.fullmatch(line)
            if not match:
                stats["source_unsupported"] += 1
                continue
            seen += 1
            rule = f"HOST-SUFFIX,{match.group(1).lower()},REJECT"
            if rule.lower() in merged:
                stats["source_duplicate"] += 1
            else:
                merged[rule.lower()] = rule
                stats["source_added"] += 1
        if seen < 1000:
            raise ValueError("QX 上游有效规则数量异常，拒绝发布")
        stats["source_valid"] += seen
        stats["sources_ok"] += 1
    return sorted(merged.values(), key=str.lower), stats


def download_source(url):
    req = urllib.request.Request(url, headers={"User-Agent": "rules-hub-qx-ads/1.0"})
    with urllib.request.urlopen(req, timeout=45) as resp:
        return resp.read(SOURCE_MAX_BYTES + 1)


def allowed_domains(white):
    return {domain for raw in white.splitlines()
            if (line := raw.strip().lower()).startswith("@@")
            if (domain := parse_domain(line[2:]))}


def is_allowed(domain, allow):
    labels = domain.split(".")
    return any(".".join(labels[i:]) in allow for i in range(len(labels) - 1))


def filter_qx_allowlist(rules, white):
    allow = allowed_domains(white)
    retained = []
    removed = 0
    for rule in rules:
        match = QX_SUFFIX.fullmatch(rule)
        if match and is_allowed(match.group(1).lower(), allow):
            removed += 1
        else:
            retained.append(rule)
    return retained, removed


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--black", type=Path, default=ROOT / "adguard/dist/adguard-black.txt")
    p.add_argument("--white", type=Path, default=ROOT / "adguard/dist/adguard-white.txt")
    p.add_argument("--output", type=Path, default=ROOT / "Quantumult/dist/Quantumult-ads.list")
    p.add_argument("--sources", type=Path, default=SOURCE_FILE)
    args = p.parse_args()
    black = args.black.read_text(encoding="utf-8-sig")
    white = args.white.read_text(encoding="utf-8-sig")
    rules, stats = convert(black, white)
    if not rules or stats["black_input"] == 0:
        raise ValueError("no convertible ad-domain rules; refusing to overwrite existing output")
    sources = [line.strip() for line in args.sources.read_text(encoding="utf-8").splitlines()
               if line.strip() and not line.lstrip().startswith("#")]
    if not sources or any(not url.startswith("https://") for url in sources):
        raise ValueError("QX upstream list is empty or contains non-HTTPS URL")
    rules, source_stats = merge_qx_sources(rules, sources, download_source)
    stats.update(source_stats)
    rules, excluded_after_merge = filter_qx_allowlist(rules, white)
    stats["source_allow_excluded"] = excluded_after_merge
    args.output.parent.mkdir(parents=True, exist_ok=True)
    content = "# Quantumult X ad-domain rules: AdGuard conversion + native QX upstream\n# Sources: Quantumult/ads-sources.txt; only HOST-SUFFIX reject rules; deduped.\n" + "\n".join(rules) + "\n"
    temporary = args.output.with_name(args.output.name + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(args.output)
    report = args.output.with_name("Quantumult-ads-STATS.md")
    report.write_text("# AdGuard → QX 广告分流转换与上游合并统计\n\n" + "".join(f"- {k}: {v}\n" for k, v in sorted(stats.items())) + "\nAdGuard 纯域名转换后与 `ads-sources.txt` 中的 QX 原生 HOST-SUFFIX/REJECT 上游去重。白名单只从 AdGuard 转换候选中排除，不生成 DIRECT。\n", encoding="utf-8")
    print("QX ads:", dict(stats))


if __name__ == "__main__":
    main()
