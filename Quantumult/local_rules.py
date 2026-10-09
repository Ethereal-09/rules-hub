"""Append personal [rewrite_remote] entries into the base QX profile.

Entries are read from Quantumult/rewrite-local.txt and use the same line syntax
as the upstream profile's own rewrite_remote section:

    <conf URL>, tag=<label>, update-interval=86400, opt-parser=false, enabled=true

Appending happens before mirroring, so a listed conf file is downloaded and
rewritten to this repository's Raw address exactly like an upstream entry.
"""
import re

SECTION_RE = re.compile(r"^\s*\[([^\]]+)\]\s*(?:\r?\n)?$")


def load_local_rules(path):
    """Read rewrite-local.txt; return active entry lines (comments/blank dropped)."""
    if not path.exists():
        return []
    rules = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", ";", "//")):
            continue
        rules.append(line)
    return rules


def inject_local_rules(text, rules, rewrite):
    """Append entries at the END of the [rewrite_remote] block; create it if absent.

    `rewrite` receives an entry line and must return the (possibly mirrored) line.
    """
    if not rules:
        return text
    processed = [rewrite(rule) for rule in rules]

    lines = text.splitlines(keepends=True)

    # Locate the [rewrite_remote] header and the start of the next section.
    start = None
    end = None
    for i, line in enumerate(lines):
        m = SECTION_RE.match(line)
        if not m:
            continue
        if start is None:
            if m.group(1).lower() == "rewrite_remote":
                start = i
        elif end is None:
            end = i
            break

    if start is None:
        out = list(lines)
        if out and not out[-1].endswith("\n"):
            out[-1] += "\n"
        out.append("\n[rewrite_remote]\n")
        _emit(out, processed)
        return "".join(out)

    if end is None:
        end = len(lines)

    # Walk back over trailing blank lines so the addition sits tight after upstream rows.
    insert_at = end
    while insert_at > start + 1 and not lines[insert_at - 1].strip():
        insert_at -= 1

    out = list(lines[:insert_at])
    _emit(out, processed)
    out.extend(lines[insert_at:])
    return "".join(out)


def _emit(out, processed):
    out.append("\n# ======= 个人追加 ======= #\n")
    for r in processed:
        out.append(r + "\n")
