"""Apply explicit user overrides to an upstream QX profile; fail on drift.

A patch targets one exact upstream line by SHA-256. This intentionally avoids
silently overriding a changed or removed upstream setting. Additions remain in
rewrite-local.txt and policy-local.txt.
"""
import hashlib
import json
import re
from pathlib import Path

SECTION = re.compile(r"^\[([^\]]+)\]\s*$", re.I)


class PatchConflict(ValueError):
    pass


def digest(line):
    return hashlib.sha256(line.strip().encode("utf-8")).hexdigest()


def active_sections(text):
    section = None
    for line in text.splitlines():
        match = SECTION.match(line)
        if match:
            section = match.group(1).lower()
        elif section and line.strip() and not line.lstrip().startswith(("#", ";", "//")):
            yield section, line.strip()


def load_patches(path):
    data = json.loads(Path(path).read_text(encoding="utf-8")) if Path(path).exists() else []
    if not isinstance(data, list):
        raise ValueError("overrides.json must be an array")
    for patch in data:
        if (not isinstance(patch, dict) or patch.get("operation") not in ("remove", "replace")
                or not isinstance(patch.get("section"), str)
                or not isinstance(patch.get("match"), str)
                or not re.fullmatch(r"[0-9a-f]{64}", patch.get("expected_sha256", ""))
                or (patch["operation"] == "replace" and not isinstance(patch.get("value"), str))):
            raise ValueError("invalid override entry")
    return data


def apply_patches(text, patches):
    lines = text.splitlines(keepends=True)
    section = None
    targets = {}
    for index, line in enumerate(lines):
        match = SECTION.match(line.strip())
        if match:
            section = match.group(1).lower()
        elif section and line.strip() and not line.lstrip().startswith(("#", ";", "//")):
            # Filter/local rewrite rules have a shared first field; identify the
            # full line instead of just DOMAIN-SUFFIX / URL regex.
            value = line.strip()
            key = value if section in ("filter_local", "rewrite_local") else value.split(",", 1)[0]
            targets.setdefault((section, key), []).append(index)
    changes = {}
    for patch in patches:
        key = (patch["section"].lower(), patch["match"])
        positions = targets.get(key, [])
        if len(positions) != 1:
            raise PatchConflict(f"上游条目缺失或重复：[{key[0]}] 指纹 {digest(key[1])[:12]}")
        index = positions[0]
        if digest(lines[index]) != patch["expected_sha256"]:
            raise PatchConflict(f"上游已更改个人覆盖的条目：[{key[0]}] 指纹 {digest(key[1])[:12]}")
        if index in changes:
            raise PatchConflict(f"个人覆盖重复：[{key[0]}] 指纹 {digest(key[1])[:12]}")
        ending = "\r\n" if lines[index].endswith("\r\n") else "\n" if lines[index].endswith("\n") else ""
        value = patch.get("value", "") if patch["operation"] == "replace" else ""
        if "\n" in value or "\r" in value:
            raise ValueError("replacement must be one line")
        changes[index] = value + ending if value else ""
    return "".join(changes.get(i, line) for i, line in enumerate(lines))


def section_state(text):
    """Only hashes/counts are persisted; never store upstream credentials."""
    sections = {}
    for name, line in active_sections(text):
        sections.setdefault(name, []).append(digest(line))
    return {name: {"count": len(items), "sha256": digest("\n".join(items)), "entries": items}
            for name, items in sorted(sections.items())}


def state_report(previous, current):
    changes = []
    for name in sorted(previous.keys() | current.keys()):
        if previous.get(name) != current.get(name):
            before = previous.get(name, {}).get("count", 0)
            after = current.get(name, {}).get("count", 0)
            old_entries = set(previous.get(name, {}).get("entries", []))
            new_entries = set(current.get(name, {}).get("entries", []))
            added = sorted(new_entries - old_entries)
            removed = sorted(old_entries - new_entries)
            details = (f"新增 {len(added)}，移除 {len(removed)}；"
                       f"指纹 +{','.join(x[:10] for x in added[:8]) or '-'}"
                       f" / -{','.join(x[:10] for x in removed[:8]) or '-'}")
            changes.append(f"[{name}] {before} → {after} 条；{details}")
    return changes
