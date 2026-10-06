#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rules-hub 邮件通知脚本（纯文本版，汇总）
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
import re
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


def parse_summary(stats_text):
    """从 STATS.md 头部解析汇总数字。"""
    info = {"sources": "", "black": "", "white": ""}
    for line in stats_text.splitlines():
        line = line.strip()
        if line.startswith("- 上游源："):
            info["sources"] = line[len("- 上游源："):].strip()
        elif line.startswith("- 黑名单规则："):
            info["black"] = line[len("- 黑名单规则："):].strip().replace("**", "")
        elif line.startswith("- 白名单规则："):
            info["white"] = line[len("- 白名单规则："):].strip().replace("**", "")
    return info


def fmt_rule(s):
    """把 '220169 条（去重 15234）' 格式化成 '220,169 条（去重 15,234）'"""
    def repl(m):
        return format(int(m.group(0)), ",")
    return re.sub(r"\d+", repl, s)


def parse_fail_sources(stats_text):
    """从源统计表里找出 FAIL 的源名。"""
    fails = []
    for line in stats_text.splitlines():
        line = line.strip()
        if not line.startswith("|") or "上游源" in line or line.startswith("|---"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) >= 5 and cells[4] != "OK":
            url = cells[0].rstrip("/")
            name = url.split("/")[-1]
            if name in ("", "filter.txt", "rule.txt", "adblockdns.txt", "dns.txt", "adguard.txt"):
                parts = [p for p in url.split("/") if p]
                if len(parts) >= 2:
                    name = parts[-2]
            fails.append(name)
    return fails


def build_text(platform, status, stats_text, build_info=None, black_n=0, white_n=0):
    bj = (datetime.now(timezone.utc) + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M")
    st = "成功" if status == "success" else "失败"
    mark = "✅" if status == "success" else "❌"

    bad_url = f"https://raw.githubusercontent.com/Ethereal-09/rules-hub/main/{platform}/dist/adguard-black.txt"
    ok_url = f"https://raw.githubusercontent.com/Ethereal-09/rules-hub/main/{platform}/dist/adguard-white.txt"

    info = parse_summary(stats_text)
    fails = parse_fail_sources(stats_text)

    lines = []
    lines.append(f"{mark} rules-hub · {platform} 合并{st}")
    lines.append(f"时间：{bj}")
    if build_info:
        repo, bstatus, sha = build_info
        lines.append(f"仓库：{repo}")
        lines.append(f"状态：{'成功' if bstatus == 'success' else '失败'}")
        lines.append(f"提交：{sha}")

    lines.append("")
    if info["sources"]:
        lines.append(f"上游源：{info['sources']}")
    lines.append(f"黑名单：{fmt_rule(info['black']) if info['black'] else f'{black_n:,} 条'}")
    lines.append(f"白名单：{fmt_rule(info['white']) if info['white'] else f'{white_n:,} 条'}")

    if fails:
        lines.append("")
        lines.append(f"⚠️ 拉取失败：{'、'.join(fails)}")

    lines.append("")
    lines.append("订阅地址：")
    lines.append(f"黑名单  {bad_url}")
    lines.append(f"白名单  {ok_url}")

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

    info = parse_summary(stats_text)
    subject = f"rules-hub {platform} {'✅ 合并成功' if status == 'success' else '❌ 合并失败'}"

    repo = os.environ.get("GITHUB_REPOSITORY", "")
    sha = os.environ.get("GITHUB_SHA", "")[:7]
    build_info = (repo, status, sha) if repo and sha else None

    body = build_text(platform, status, stats_text, build_info, black_n, white_n)

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
