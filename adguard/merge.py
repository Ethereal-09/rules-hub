#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AdGuard Home 规则合并器

- 黑名单源（black-sources.txt）  ：上游黑名单源（URL 列表）
- 白名单源（white-sources.txt）  ：上游白名单源（URL 列表）
- 我的黑名单（my-blacklist.txt）  ：一行一个裸域名
- 我的白名单（my-whitelist.txt）  ：一行一个裸域名

合并逻辑：
  黑名单 = 上游黑名单源【合并 + 去重】 + 我的黑名单（裸域名 → ||x^）
  白名单 = 上游白名单源【合并 + 去重】（非 @@ 行也保留）
         + 黑名单源里筛出的 @@ 行
         + 我的白名单（裸域名 → @@||x^）

规则：
  - 丢弃注释（! 开头）和元数据（[...] 开头）
  - 整行小写去重（保序）
  - 不做对冲、不做跨语法翻译

输出 dist/adguard-black.txt、dist/adguard-white.txt、dist/STATS.md
"""
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone, timedelta

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

BARE_DOMAIN_RE = re.compile(
    r"^[a-z0-9](?:[a-z0-9\-]*[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9\-]*[a-z0-9])?)+$", re.I)


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def fetch(url, attempt=1):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            raw = r.read()
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


def normalize(line):
    return line.strip().lower()


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
        f"! Last modified: {ts}",
        f"! 规则数: {n}",
        "! 本文件由 GitHub Actions 自动生成，请勿手动修改",
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
    # 黑名单行（锚点：adguard-black.txt）
    new_text = re.sub(
        r"\| 黑名单（拦截） \| [0-9,，—]* \| \[订阅\]\(https://raw\.githubusercontent\.com/Ethereal-09/rules-hub/main/adguard/dist/adguard-black\.txt\)",
        lambda m: m.group(0).replace(re.search(r"[0-9,，—]+", m.group(0)).group(0), f"{black_n:,}", 1),
        new_text,
    )
    # 白名单行（锚点：adguard-white.txt）
    new_text = re.sub(
        r"\| 白名单（放行） \| [0-9,，—]* \| \[订阅\]\(https://raw\.githubusercontent\.com/Ethereal-09/rules-hub/main/adguard/dist/adguard-white\.txt\)",
        lambda m: m.group(0).replace(re.search(r"[0-9,，—]+", m.group(0)).group(0), f"{white_n:,}", 1),
        new_text,
    )
    # 上次更新时间
    new_text = re.sub(r"上次更新时间：.*", f"上次更新时间：{ts}", new_text, count=1)
    if new_text != text:
        with open(readme, "w", encoding="utf-8") as f:
            f.write(new_text)
        log(f"  -> README 已同步：黑 {black_n:,} 白 {white_n:,}")


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
                white_out.append(line)   # 黑源里的白名单 → 进白名单
                add_w += 1
            else:
                black_out.append(line)
                add_b += 1
        log(f"  -> 读取 {total}, 黑 {add_b}, 白 {add_w}")
        stats.append((url, total, add_b, add_w, "OK"))

    # ---- 拉白名单源（非 @@ 行也保留）----
    for idx, url in enumerate(white_srcs, 1):
        log(f"[白 {idx}/{len(white_srcs)}] {url}")
        text = fetch(url)
        if text is None:
            stats.append((url, 0, 0, 0, "FAIL"))
            continue
        total = add_w = 0
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

    # ---- 统一小写，再去重（保序）----
    raw_black_n = len(black_out)
    raw_white_n = len(white_out)
    black_out = dedupe_preserve_order(l.lower() for l in black_out)
    white_out = dedupe_preserve_order(l.lower() for l in white_out)
    dedup_black = raw_black_n - len(black_out)
    dedup_white = raw_white_n - len(white_out)

    ts = (datetime.now(timezone.utc) + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")

    with open(OUT_BLACK, "w", encoding="utf-8") as f:
        f.write(file_header("AdGuard Home 黑名单", ts, len(black_out)))
        for l in black_out:
            f.write(l + "\n")
    with open(OUT_WHITE, "w", encoding="utf-8") as f:
        f.write(file_header("AdGuard Home 白名单", ts, len(white_out)))
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
