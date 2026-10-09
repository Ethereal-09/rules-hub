"""Append personal [policy] entries into the base QX profile.

Entries are read from Quantumult/policy-local.txt and use the same line syntax
as the upstream profile's own policy section:

    url-latency-benchmark=<组名>, server-tag-regex=<正则>, check-interval=1200, tolerance=0, img-url=<图标>

Appending happens before mirroring, so any mirrored resource referenced here is
processed exactly like an upstream entry.
"""
import re

SECTION_RE = re.compile(r"^\s*\[([^\]]+)\]\s*(?:\r?\n)?$")


def load_local_rules(path):
    """Read policy-local.txt; return active entry lines (comments/blank dropped)."""
    if not path.exists():
        return []
    rules = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", ";", "//")):
            continue
        rules.append(line)
    return rules


def _emit(out, processed):
    out.append("\n# ======= 个人追加策略组 ======= #\n")
    for r in processed:
        out.append(r + "\n")


def inject_local_policies(text, rules, rewrite=None):
    """Append entries at the END of the [policy] block; create it if absent.

    `rewrite` (optional) receives an entry line and may return a transformed line.
    """
    if not rules:
        return text
    processed = [rewrite(r) if rewrite else r for r in rules]

    lines = text.splitlines(keepends=True)

    start = None
    end = None
    for i, line in enumerate(lines):
        m = SECTION_RE.match(line)
        if not m:
            continue
        if start is None:
            if m.group(1).lower() == "policy":
                start = i
        elif end is None:
            end = i
            break

    if start is None:
        out = list(lines)
        if out and not out[-1].endswith("\n"):
            out[-1] += "\n"
        out.append("\n[policy]\n")
        _emit(out, processed)
        return "".join(out)

    if end is None:
        end = len(lines)

    # Walk back over trailing blanks so the addition sits tight after upstream rows.
    insert_at = end
    while insert_at > start + 1 and not lines[insert_at - 1].strip():
        insert_at -= 1

    out = list(lines[:insert_at])
    _emit(out, processed)
    out.extend(lines[insert_at:])
    return "".join(out)
