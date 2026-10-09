#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rules-hub AdGuard Home 邮件通知（纯文本汇总）

- 读 <platform>/dist/STATS.md 与黑白名单产物，生成纯文本邮件
- 附带本次触发提交的完整说明、运行记录链接、失败源明细
- 通过 163 SMTP 发送

用法：
  python3 .github/notify.py <platform_dir> <success|failure>

环境变量（GitHub Secret / Actions 默认）：
  SMTP_USER   163 邮箱地址
  SMTP_PASS   163 授权码
  SMTP_TO     收件邮箱
  GITHUB_REPOSITORY / GITHUB_SHA / GITHUB_RUN_ID / GITHUB_TOKEN  由 Actions 提供
"""
import json
import os
import re
import sys
import smtplib
import urllib.request
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


def fetch_commit_note(repo, revision, token):
    """Return (subject, body_lines) of the triggering commit, or None."""
    if not (repo and revision and token):
        return None
    url = f"https://api.github.com/repos/{repo}/commits/{revision}"
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "rules-hub-notify",
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.load(r)
    except Exception as exc:
        print(f"读取提交说明失败（忽略）：{exc}")
        return None
    message = (data.get("commit") or {}).get("message", "")
    if not message:
        return None
    parts = [ln.strip() for ln in message.splitlines()]
    subject = parts[0] if parts else ""
    body = [ln for ln in parts[1:] if ln]
    return subject, body


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
    """从源统计表里找出 FAIL 的源，返回 (名称, 读取数, 状态)。"""
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
            fails.append((name, cells[1], cells[4]))
    return fails


def build_text(platform, status, stats_text, build_info=None, black_n=0, white_n=0,
               commit_note=None, run_id="", run_url=""):
    bj = (datetime.now(timezone.utc) + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M")
    st = "成功" if status == "success" else "失败"
    mark = "✅" if status == "success" else "❌"

    repo = build_info[0] if build_info and build_info[0] else os.environ.get("GITHUB_REPOSITORY", "Ethereal-09/rules-hub")
    bad_url = f"https://raw.githubusercontent.com/{repo}/main/{platform}/dist/adguard-black.txt"
    ok_url = f"https://raw.githubusercontent.com/{repo}/main/{platform}/dist/adguard-white.txt"

    # A failed run may find STATS.md and dist from a previous successful run.
    # Never present those numbers or failed-source rows as this run's results.
    info = parse_summary(stats_text) if status == "success" else {"sources": "", "black": "", "white": ""}
    fails = parse_fail_sources(stats_text) if status == "success" else []

    lines = []
    lines.append(f"{mark} rules-hub · {platform} 合并{st}")
    lines.append(f"北京时间：{bj}")
    if build_info:
        repo, bstatus, sha = build_info
        lines.append(f"仓库：{repo}")
        lines.append(f"触发提交：{sha}")
    if run_url:
        lines.append(f"运行记录：{run_url}")

    if commit_note:
        subject, body = commit_note
        lines.append("")
        lines.append("本次改动：")
        if subject:
            lines.append(f"  {subject}")
        for ln in body:
            lines.append(f"  {re.sub(r'^[-*] ', '', ln)}")
    else:
        lines.append("本次改动：未能读取提交说明")

    lines.append("")
    if status == "success":
        if info["sources"]:
            lines.append(f"上游源：{info['sources']}")
        lines.append(f"黑名单：{fmt_rule(info['black']) if info['black'] else f'{black_n:,} 条'}")
        lines.append(f"白名单：{fmt_rule(info['white']) if info['white'] else f'{white_n:,} 条'}")
    else:
        lines.append("本轮未发布；本地 STATS 与产物可能属于旧版，不作为本轮结果。")

    if fails:
        lines.append("")
        lines.append(f"⚠️ 拉取失败 {len(fails)} 个：")
        for name, total, state in fails:
            lines.append(f"  {name}（读取 {total}，{state}）")

    lines.append("")
    if status == "success":
        lines.append("订阅地址：")
        lines.append(f"黑名单  {bad_url}")
        lines.append(f"白名单  {ok_url}")
    else:
        lines.append("构建或发布失败，请打开运行记录查看失败步骤；不要把旧产物误认为已更新。")

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
        print("缺少 SMTP_USER / SMTP_PASS / SMTP_TO 环境变量，跳过通知")
        return

    dist_dir = os.path.join(platform, "dist")
    stats_text = read(os.path.join(dist_dir, "STATS.md"))
    black_text = read(os.path.join(dist_dir, "adguard-black.txt"))
    white_text = read(os.path.join(dist_dir, "adguard-white.txt"))

    black_n = sum(1 for l in black_text.splitlines() if l.strip() and not l.startswith("!"))
    white_n = sum(1 for l in white_text.splitlines() if l.strip() and not l.startswith("!"))

    subject = f"rules-hub {platform} {'✅ 合并成功' if status == 'success' else '❌ 合并失败'}"

    repo = os.environ.get("GITHUB_REPOSITORY", "")
    sha = os.environ.get("GITHUB_SHA", "")[:12]
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    token = os.environ.get("GITHUB_TOKEN", "")
    run_url = f"https://github.com/{repo}/actions/runs/{run_id}" if repo and run_id else ""

    build_info = (repo, status, sha) if repo and sha else None
    commit_note = fetch_commit_note(repo, sha, token)

    body = build_text(platform, status, stats_text, build_info, black_n, white_n,
                      commit_note, run_id, run_url)

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
        # 通知失败不改判构建结果，与 QX 通知保持一致。


if __name__ == "__main__":
    main()
