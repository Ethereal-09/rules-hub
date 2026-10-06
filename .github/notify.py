#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rules-hub 邮件通知脚本（纯文本版）
- 读 dist/STATS.md + 黑白名单文件，生成纯文本邮件
- 通过 163 SMTP 发送
- 供 GitHub Actions 调用

用法：
  python3 .github/notify.py <platform_dir> <success|failure>

环境变量（GitHub Secret）：
  SMTP_USER  163 邮箱地址
  SMTP_PASS  163 授权码
  SMTP_TO    收件邮箱
"""
import os
import sys
import smtplib
from datetime import datetime, timezone, timedelta
from email.mime.text import MIMEText
from email.header import Header

SMTP_HOST = "smtp.163.com"
SMTP_PORT = 465  # SSL


def read(path):
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def parse_stats(stats_text):
    """解析 STATS.md 的源统计表 → [(url, 读取, 新增黑, 新增白, 状态)]"""
    rows = []
    for line in stats_text.splitlines():
        line = line.strip()
        if not line.startswith("|") or "上游源" in line or line.startswith("|---"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) >= 5:
            rows.append(cells[:5])
    return rows


def short_name(url):
    """把完整 URL 缩成易读的源名。"""
    url = url.rstrip("/")
    name = url.split("/")[-1]
    if name in ("", "filter.txt", "rule.txt", "adblockdns.txt", "dns.txt", "adguard.txt"):
        parts = [p for p in url.split("/") if p]
        if len(parts) >= 2:
            return parts[-2]
    return name


def build_text(platform, status, stats_text, black_n, white_n, build_info=None):
    bj = (datetime.now(timezone.utc) + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M")
    st = "成功" if status == "success" else "失败"
    mark = "✅" if status == "success" else "❌"

    bad_url = f"https://raw.githubusercontent.com/Ethereal-09/rules-hub/main/{platform}/dist/adguard-black.txt"
    ok_url = f"https://raw.githubusercontent.com/Ethereal-09/rules-hub/main/{platform}/dist/adguard-white.txt"

    lines = []
    lines.append(f"{mark} rules-hub {platform} 合并{st}")
    lines.append(f"时间：{bj}")
    if build_info:
        repo, bstatus, sha = build_info
        lines.append(f"仓库：{repo}")
        lines.append(f"状态：{'成功' if bstatus == 'success' else '失败'}")
        lines.append(f"提交：{sha}")

    lines.append("")
    lines.append(f"黑名单：{black_n:,}")
    lines.append(f"白名单：{white_n:,}")

    rows = parse_stats(stats_text)
    if rows:
        lines.append("")
        lines.append("上游源统计：")
        for url, total, ab, aw, st2 in rows:
            status_txt = "OK" if st2 == "OK" else "FAIL"
            lines.append(f"  {short_name(url)}  读取{int(total):,}  新增黑{int(ab):,}  新增白{int(aw):,}  {status_txt}")

    fail_rows = [r for r in rows if r[4] != "OK"]
    if fail_rows:
        lines.append("")
        lines.append("拉取失败的源：" + "、".join(short_name(u) for u, *_ in fail_rows))

    lines.append("")
    lines.append("订阅地址：")
    lines.append(f"  黑名单 {bad_url}")
    lines.append(f"  白名单 {ok_url}")

    lines.append("")
    lines.append("—— rules-hub 自动生成，每 8 小时更新")

    return "\n".join(lines)


def main():
    if len(sys.argv) < 3:
        print("用法: notify.py <platform_dir> <success|failure>")
        sys.exit(1)
    platform = sys.argv[1]
    status = sys.argv[2]

    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_PASS", "")
    smtp_to = os.environ.get("SMTP_TO", "")

    if not all([smtp_user, smtp_pass, smtp_to]):
        print("缺少 SMTP_USER / SMTP_PASS / SMTP_TO 环境变量")
        sys.exit(1)

    dist_dir = os.path.join(platform, "dist")
    stats_text = read(os.path.join(dist_dir, "STATS.md"))
    black_text = read(os.path.join(dist_dir, "adguard-black.txt"))
    white_text = read(os.path.join(dist_dir, "adguard-white.txt"))

    black_n = sum(1 for l in black_text.splitlines() if l.strip() and not l.startswith("!"))
    white_n = sum(1 for l in white_text.splitlines() if l.strip() and not l.startswith("!"))

    subject = f"rules-hub {platform} {'✅ 合并成功' if status == 'success' else '❌ 合并失败'} · 黑 {black_n:,} 白 {white_n:,}"

    repo = os.environ.get("GITHUB_REPOSITORY", "")
    sha = os.environ.get("GITHUB_SHA", "")[:7]
    build_info = (repo, status, sha) if repo and sha else None

    body = build_text(platform, status, stats_text, black_n, white_n, build_info)

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = smtp_user
    msg["To"] = smtp_to

    try:
        server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=30)
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, [smtp_to], msg.as_string())
        server.quit()
        print(f"✅ 邮件已发送: {subject}")
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
