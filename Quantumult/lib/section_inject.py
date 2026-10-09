"""Generic appender for personal entries in an INI-style QX profile.

Both personal rewrites ([rewrite_remote]) and personal policies ([policy]) are
plain line lists that must be appended at the END of an existing section, right
before the next section header, or in a freshly created section when absent.

Keeping one implementation avoids the two near-identical copies drifting apart.
"""
import re

SECTION_RE = re.compile(r"^\s*\[([^\]]+)\]\s*(?:\r?\n)?$")


def load_entries(path):
    """Read a personal-rules file; return active lines (comments/blank dropped)."""
    if not path.exists():
        return []
    entries = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith(("#", ";", "//")):
            continue
        entries.append(line)
    return entries


def inject_entries(text, section_name, entries, banner, transform=None):
    """Append entries at the END of `section_name`; create the section if absent.

    `transform` (optional) receives each entry and returns the final line, which
    lets the caller mirror URLs before the profile is emitted.
    """
    if not entries:
        return text
    processed = [transform(e) if transform else e for e in entries]
    target = section_name.lower()

    lines = text.splitlines(keepends=True)

    start = None
    end = None
    for i, line in enumerate(lines):
        m = SECTION_RE.match(line)
        if not m:
            continue
        if start is None:
            if m.group(1).lower() == target:
                start = i
        elif end is None:
            end = i
            break

    if start is None:
        out = list(lines)
        if out and not out[-1].endswith("\n"):
            out[-1] += "\n"
        out.append(f"\n[{section_name}]\n")
        _emit(out, banner, processed)
        return "".join(out)

    if end is None:
        end = len(lines)

    # Walk back over trailing blank lines so the addition sits tight after upstream rows.
    insert_at = end
    while insert_at > start + 1 and not lines[insert_at - 1].strip():
        insert_at -= 1

    out = list(lines[:insert_at])
    _emit(out, banner, processed)
    out.extend(lines[insert_at:])
    return "".join(out)


def _emit(out, banner, processed):
    out.append(f"\n# ======= {banner} ======= #\n")
    for line in processed:
        out.append(line + "\n")
