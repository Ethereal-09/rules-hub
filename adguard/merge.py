#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AdGuard Home 规则合并器

黑源仅将纯 DNS 域名拦截写入黑名单，黑源中的 `@@` 例外写入白名单。
白源全部非注释规则保留在白名单，合并并去重，不再按语法筛选。
注意：白源中可能混有阻断/改写/网页规则，白名单不保证全部为 DNS 放行规则。
个人裸域名仍按黑白分别追加；现有订阅路径不变。
"""
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone, timedelta

DNS_DOMAIN = r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z](?:[a-z0-9-]{0,61}[a-z0-9])?"
DNS_BLACK = re.compile(r"\|\|(" + DNS_DOMAIN + r")\^(\$important)?", re.I)
DNS_WHITE = re.compile(r"@@\|\|(" + DNS_DOMAIN + r")\^", re.I)

ROOT = os.path.dirname(os.path.abspath(__file__))
BLACK_SRC = os.path.join(ROOT, "black-sources.txt")
WHITE_SRC = os.path.join(ROOT, "white-sources.txt")
MY_BLACK = os.path.join(ROOT, "my-blacklist.txt")
MY_WHITE = os.path.join(ROOT, "my-whitelist.txt")
OUT_DIR = os.path.join(ROOT, "dist")
OUT_BLACK = os.path.join(OUT_DIR, "adguard-black.txt")
OUT_WHITE = os.path.join(OUT_DIR, "adguard-white.txt")

UA = "Mozilla/5.0 (compatible; RulesHubBot/1.0)"
TIMEOUT = 60
RETRY = 3
REPO = os.environ.get("GITHUB_REPOSITORY", "Ethereal-09/rules-hub")
REPO_URL = f"https://github.com/{REPO}"
MAX_SOURCE_BYTES = 32 * 1024 * 1024
MIN_BLACK_RULES = 1000
MIN_WHITE_RULES = 10
MIN_PREVIOUS_RATIO = 0.70

BARE_DOMAIN_RE = re.compile(
    r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+$", re.I)


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def fetch(url, attempt=1):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            raw = r.read(MAX_SOURCE_BYTES + 1)
        if not raw or len(raw) > MAX_SOURCE_BYTES:
            raise ValueError("上游源为空或超过 32 MiB 上限")
        # Avoid treating a CDN error page returned with HTTP 200 as a filter.
        if raw[:512].lstrip().lower().startswith((b"<!doctype html", b"<html")):
            raise ValueError("上游返回 HTML 错误页")
        for enc in ("utf-8-sig", "utf-8", "latin-1"):
            try:
                return raw.decode(enc)
            except UnicodeDecodeError:
                continue
        return raw.decode("utf-8", errors="replace")
    except Exception as e:
        if attempt < RETRY:
            log(f"  ! 第 {attempt} 次失败 ({e})，2s 后重试")
            urllib.request.urlcleanup()
            import time
            time.sleep(2)
            return fetch(url, attempt + 1)
        log(f"  x 放弃: {url} ({e})")
        return None


def load_lines(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [ln.strip() for ln in f if ln.strip() and not ln.strip().startswith("#")]


def is_dropped(line):
    """丢弃注释（! 开头）和元数据（[...] 开头）。"""
    s = line.strip()
    return (not s) or s.startswith("!") or s.startswith("[")


PLAIN_DOMAIN = re.compile(r"^(?P<exception>@@)?\|\|(?P<domain>[A-Za-z0-9.-]+)\^$")


def normalize(line):
    """Only domain-only anchors are case-insensitive; never lowercase paths/CSS."""
    line = line.strip()
    match = PLAIN_DOMAIN.fullmatch(line)
    if match and BARE_DOMAIN_RE.fullmatch(match.group("domain")):
        return f"{'@@' if match.group('exception') else ''}||{match.group('domain').lower()}^"
    if BARE_DOMAIN_RE.fullmatch(line):
        return line.lower()
    return line


def is_exception(line):
    """Semantic exception, including cosmetic exceptions and badfilter disable."""
    return line.startswith("@@") or "#@#" in line or bool(re.search(r"\$[^\s]*\bbadfilter\b", line, re.I))


def dedupe_preserve_order(items):
    seen = set()
    out = []
    for item in items:
        key = normalize(item)
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def bare_to_black(d):
    """裸域名 → 黑名单规则 ||x^"""
    return f"||{d}^"


def bare_to_white(d):
    """裸域名 → 白名单规则 @@||x^"""
    return f"@@||{d}^"


def parse_bare(path):
    """读我的黑白名单文件，返回裸域名列表（非法的丢弃）。"""
    out = []
    for ln in load_lines(path):
        s = ln.strip()
        if BARE_DOMAIN_RE.match(s):
            out.append(s.lower())
        else:
            log(f"  ! 忽略非法裸域名: {ln}")
    return dedupe_preserve_order(out)


def file_header(title, ts, n, extra=""):
    h = [
        f"! Title: {title}",
        f"! Homepage: {REPO_URL}",
        f"! Last modified: {ts}",
        f"! 规则数: {n}",
        "!",
        "! 本文件由 GitHub Actions 自动生成，每 8 小时更新，请勿手动修改。",
        "! 合并自多个公开上游规则，版权归各上游作者所有。",
        f"! 上游来源清单：{REPO_URL}/blob/main/SOURCES.md",
        "!",
        "! 免责声明：本规则库仅供个人学习与研究使用，按「现状」提供，",
        "!           不附带任何明示或暗示的担保。因使用本规则导致的任何",
        "!           直接或间接损失，由使用者自行承担。请自行评估风险，",
        "!           导入前备份现有配置。",
    ]
    if extra:
        h.append(extra)
    h.append("")
    return "\n".join(h) + "\n"


def update_readme(black_n, white_n, ts):
    """同步仓库根 README 的黑白数字 + 上次更新时间。"""
    readme = os.path.normpath(os.path.join(ROOT, "..", "README.md"))
    if not os.path.exists(readme):
        return
    try:
        with open(readme, "r", encoding="utf-8") as f:
            text = f.read()
    except Exception:
        return
    new_text = text
    # 只匹配 AdGuard 表格首两格，避免对 QX 行或链接作替换。
    for label, count in (("黑名单", black_n), ("白名单", white_n)):
        pattern = rf"(?m)^(\| \*\*{label}\*\* · [^|]+\|\s*)(?:[\d,，]+|—)(\s*\|)"
        new_text, found = re.subn(pattern, lambda m: f"{m.group(1)}{count:,}{m.group(2)}", new_text, count=1)
        if found != 1:
            raise ValueError(f"README AdGuard {label}行未找到，拒绝静默漏更新")
    # 同步徽章上的数字（AdGuard_黑名单-258k / AdGuard_白名单-32）
    def short(n):
        return f"{n/1000:.0f}k" if n >= 10000 else str(n)
    for badge_label, count in (("黑名单", black_n), ("白名单", white_n)):
        pattern = rf"(badge/AdGuard_{badge_label}-)([^-\?]+)(-)"
        new_text, found = re.subn(pattern, lambda m: f"{m.group(1)}{short(count)}{m.group(3)}", new_text, count=1)
        if found != 1:
            raise ValueError(f"README 徽章 AdGuard {badge_label} 未找到，拒绝静默漏更新")
    # 上次更新时间（README 里是 "上次更新：—"）
    new_text = re.sub(r"上次更新：.*?(?=</sub>)", f"上次更新：{ts} ", new_text)
    new_text = re.sub(r"上次更新时间：.*", f"上次更新时间：{ts}", new_text, count=1)
    if new_text != text:
        with open(readme, "w", encoding="utf-8") as f:
            f.write(new_text)
        log(f"  -> README 已同步：黑 {black_n:,} 白 {white_n:,}")


def validate_output(stats, black_count, white_count, previous_black=0, previous_white=0,
                    source_migration=False):
    """Fail closed before writing any generated files."""
    failed = [url for url, total, black, white, status in stats
              if status != "OK" or black + white == 0]
    if failed:
        raise ValueError(f"上游下载失败或无有效规则：{len(failed)} 个；拒绝覆盖旧版")
    if black_count < MIN_BLACK_RULES or white_count < MIN_WHITE_RULES:
        raise ValueError("合并规则数低于安全下限，拒绝发布")
    for label, current, old in (("黑", black_count, previous_black), ("白", white_count, previous_white)):
        if old and current < old * MIN_PREVIOUS_RATIO and not source_migration:
            raise ValueError(f"{label}名单规则骤降：{old} -> {current}；拒绝发布")


def dns_black_rule(line):
    match = DNS_BLACK.fullmatch(line.strip())
    return f"||{match.group(1).lower()}^{('$important' if match.group(2) else '')}" if match else None


def dns_white_rule(line):
    match = DNS_WHITE.fullmatch(line.strip())
    return f"@@||{match.group(1).lower()}^" if match else None


# A deliberate source-list change reduces output by design; the shrink guard would
# otherwise block the very commit that performs the migration. Each entry below is
# a one-shot exemption keyed on the previous source count recorded in STATS.md,
# narrowed by the first and last source currently configured.
SOURCE_MIGRATIONS = [
    # 11 -> 8：换用用户指定的八源
    {"previous": "上游源：11 个", "first": "damengzhu/banad/main/jiekouAD.txt",
     "last": "2771936993/HG/main/hg1.txt"},
    # 8 -> 7：移除 2771936993/HG（含大量 CDN/DNS 误杀）
    {"previous": "上游源：8 个", "first": "damengzhu/banad/main/jiekouAD.txt",
     "last": "rssvcn/qy-Ads-Rule/main/black.txt"},
]


def is_source_migration(black_srcs):
    """True when the current run performs a declared, one-time source migration."""
    stats_path = os.path.join(OUT_DIR, "STATS.md")
    if not os.path.isfile(stats_path):
        return False
    with open(stats_path, encoding="utf-8") as f:
        old = f.read()
    for rule in SOURCE_MIGRATIONS:
        if (rule["previous"] in old
                and black_srcs
                and rule["first"] in black_srcs[0]
                and rule["last"] in black_srcs[-1]):
            return True
    return False


def previous_count(path):
    if not os.path.isfile(path):
        return 0  # First run: absolute minimums still apply.
    with open(path, encoding="utf-8") as f:
        first = f.readline().strip()
        valid_titles = (
            "! Title: AdGuard Home DNS 专用黑名单",
            "! Title: AdGuard Home 白名单（未筛选混合规则）",
        )
        if first not in valid_titles:
            raise ValueError(f"旧产物头部异常，拒绝跳过跌幅保护：{path}")
        return sum(1 for line in f if line.strip() and not line.startswith("!"))


def main():
    black_srcs = load_lines(BLACK_SRC)
    white_srcs = load_lines(WHITE_SRC)
    my_black = parse_bare(MY_BLACK)
    my_white = parse_bare(MY_WHITE)

    log(f"黑名单源 {len(black_srcs)} 个；白名单源 {len(white_srcs)} 个；我的黑 {len(my_black)} 白 {len(my_white)}")

    if not black_srcs and not white_srcs and not my_black and not my_white:
        log("没有任何规则，退出")
        sys.exit(1)

    os.makedirs(OUT_DIR, exist_ok=True)

    black_out = []
    white_out = []
    stats = []

    # ---- 拉黑名单源 ----
    for idx, url in enumerate(black_srcs, 1):
        log(f"[黑 {idx}/{len(black_srcs)}] {url}")
        text = fetch(url)
        if text is None:
            stats.append((url, 0, 0, 0, "FAIL"))
            continue
        total = add_b = add_w = 0
        for raw in text.splitlines():
            line = raw.strip()
            if not line:
                continue
            total += 1
            if is_dropped(line):
                continue
            if line.startswith("@@"):
                white_out.append(line)
                add_w += 1
            elif (black_rule := dns_black_rule(line)):
                black_out.append(black_rule)
                add_b += 1
        log(f"  -> 读取 {total}, 黑 {add_b}, 白 {add_w}")
        stats.append((url, total, add_b, add_w, "OK"))

    # ---- 拉白名单源（不做语法筛选，保留非注释行）----
    for idx, url in enumerate(white_srcs, 1):
        log(f"[白 {idx}/{len(white_srcs)}] {url}")
        text = fetch(url)
        if text is None:
            stats.append((url, 0, 0, 0, "FAIL"))
            continue
        total = add_b = add_w = 0
        for raw in text.splitlines():
            line = raw.strip()
            if not line:
                continue
            total += 1
            if is_dropped(line):
                continue
            white_out.append(line)
            add_w += 1
        log(f"  -> 读取 {total}, 白 {add_w}")
        stats.append((url, total, 0, add_w, "OK"))

    # ---- 追加我的规则 ----
    black_out.extend(bare_to_black(d) for d in my_black)
    white_out.extend(bare_to_white(d) for d in my_white)

    # ---- 只对明确的域名规则小写，再去重（保留复杂规则原文）----
    raw_black_n = len(black_out)
    raw_white_n = len(white_out)
    black_out = dedupe_preserve_order(normalize(l) for l in black_out)
    white_out = dedupe_preserve_order(normalize(l) for l in white_out)
    dedup_black = raw_black_n - len(black_out)
    dedup_white = raw_white_n - len(white_out)

    validate_output(stats, len(black_out), len(white_out),
                    previous_count(OUT_BLACK), previous_count(OUT_WHITE),
                    source_migration=is_source_migration(black_srcs))

    ts = (datetime.now(timezone.utc) + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")

    with open(OUT_BLACK, "w", encoding="utf-8") as f:
        f.write(file_header("AdGuard Home DNS 专用黑名单", ts, len(black_out)))
        for l in black_out:
            f.write(l + "\n")
    with open(OUT_WHITE, "w", encoding="utf-8") as f:
        f.write(file_header("AdGuard Home 白名单（未筛选混合规则）", ts, len(white_out)))
        for l in white_out:
            f.write(l + "\n")

    ok_src = sum(1 for _, _, _, _, st in stats if st == "OK")
    fail_src = len(stats) - ok_src

    lines = [
        "# 合并统计",
        "",
        f"- 生成时间：{ts}",
        f"- 上游源：{len(stats)} 个（成功 {ok_src}，失败 {fail_src}）",
        f"- 黑名单规则：**{len(black_out)}** 条（去重 {dedup_black}）",
        f"- 白名单规则：**{len(white_out)}** 条（去重 {dedup_white}）",
        f"- 非 DNS 规则已跳过：{sum(total - ab - aw for _, total, ab, aw, _ in stats)} 行（含注释/元数据）",
        "- 筛选范围：黑名单仅纯域名拦截（含 `$important`）；白名单保留白源全部非注释规则与黑源 `@@` 例外，仅去重，可能含非放行规则。",
        "",
        "| 上游源 | 读取 | 新增黑 | 新增白 | 状态 |",
        "|---|---|---|---|---|",
    ]
    for url, total, ab, aw, st in stats:
        lines.append(f"| {url} | {total} | {ab} | {aw} | {st} |")
    lines.append("")
    with open(os.path.join(OUT_DIR, "STATS.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    update_readme(len(black_out), len(white_out), ts)

    log(f"完成: 黑名单 {len(black_out)}, 白名单 {len(white_out)}")


if __name__ == "__main__":
    main()
