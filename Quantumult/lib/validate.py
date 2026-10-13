"""Static consistency checks for published QX output (not an official parser)."""
import hashlib
import re
from pathlib import Path

SECTIONS = re.compile(r"^\[([^\]]+)\]\s*$", re.M)
ASSET = re.compile(r"https://(?:github\.boki\.moe/https://)?raw\.githubusercontent\.com/[^\s,]+/Quantumult/assets/((?:filter|rewrite|script)/[^\s,]+)")


def validate(profile, root, additions=()):
    root = Path(root)
    raw = Path(profile).read_bytes()
    if not 100 < len(raw) < 4 * 1024 * 1024 or b"\x00" in raw:
        raise ValueError("QX 配置为空、含 NUL 或超过限制")
    text = raw.decode("utf-8")
    sections = [m.group(1).lower() for m in SECTIONS.finditer(text)]
    if not {"general", "policy", "rewrite_remote", "filter_remote"} <= set(sections):
        raise ValueError("QX 必要配置段缺失")
    preamble = text.split("[general]", 1)[0]
    if any(line.strip() and not line.lstrip().startswith(("#", ";", "//")) for line in preamble.splitlines()):
        raise ValueError("QX 文件头存在活动配置")
    for name in additions:
        if name not in text:
            raise ValueError(f"追加项丢失：{name}")
    for relative in ASSET.findall(text):
        asset = root / "assets" / relative
        if not asset.is_file() or not asset.stat().st_size:
            raise ValueError(f"QX 镜像引用缺文件：{relative}")
    manifest = root / "SOURCES.md"
    if not manifest.is_file():
        raise ValueError("QX 缺少来源清单")
    content = manifest.read_text(encoding="utf-8")
    for rel, digest in re.findall(r"\[`assets/([^`]+)`\]\([^)]+\)\s*\|[^\n]*\|\s*`([0-9a-f]{64})`", content):
        p = root / "assets" / rel
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != digest:
            raise ValueError(f"QX 镜像 SHA-256 不匹配：{rel}")
    return len(ASSET.findall(text))
