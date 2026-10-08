#!/usr/bin/env python3
"""Conservatively derive QX ad-domain rules from merged AdGuard outputs.

Only plain domain anchors are converted. Exceptions suppress the same domain
and its subdomains; ambiguous whitelist syntax is reported, never guessed.
"""
from collections import Counter
from pathlib import Path
import argparse
import re

ROOT = Path(__file__).resolve().parents[1]
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
        if line.startswith("@@"):
            line = line[2:]
        domain = parse_domain(line)
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


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--black", type=Path, default=ROOT / "adguard/dist/adguard-black.txt")
    p.add_argument("--white", type=Path, default=ROOT / "adguard/dist/adguard-white.txt")
    p.add_argument("--output", type=Path, default=ROOT / "Quantumult/dist/Quantumult-ads.list")
    args = p.parse_args()
    black = args.black.read_text(encoding="utf-8-sig")
    white = args.white.read_text(encoding="utf-8-sig")
    rules, stats = convert(black, white)
    if not rules or stats["black_input"] == 0:
        raise ValueError("no convertible ad-domain rules; refusing to overwrite existing output")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    content = "# Quantumult X ad-domain rules derived from rules-hub/adguard\n# Only plain domain anchors; $important priority is discarded, other modifiers skipped.\n" + "\n".join(rules) + "\n"
    temporary = args.output.with_name(args.output.name + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(args.output)
    report = args.output.with_name("Quantumult-ads-STATS.md")
    report.write_text("# AdGuard → QX 广告分流转换统计\n\n" + "".join(f"- {k}: {v}\n" for k, v in sorted(stats.items())) + "\n转换纯域名锚定规则；黑名单仅含 $important 时忽略优先级并转换。其它复杂规则不做等价性承诺。白名单只从广告拦截集合中排除，不强制直连。\n", encoding="utf-8")
    print("QX ads:", dict(stats))


if __name__ == "__main__":
    main()
