#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rules-hub 邮件通知脚本
- 读 dist/STATS.md + 黑白名单文件，生成 HTML 邮件
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
import re
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
        # 取倒数第二段（仓库/组织名）
        parts = [p for p in url.split("/") if p]
        if len(parts) >= 2:
            return parts[-2]
    return name


def build_html(platform, status, stats_text, black_n, white_n, ts, build_info=None):
    bj = (datetime.now(timezone.utc) + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M")

    if status == "success":
        status_badge = '<span style="color:#34d399;">✅ 合并成功</span>'
        status_emoji = "✅"
    else:
        status_badge = '<span style="color:#f87171;">❌ 合并失败</span>'
        status_emoji = "❌"

    # 构建信息区块（repo / status / sha）—— 极简竖排
    build_html_block = ""
    if build_info:
        repo, build_status, sha = build_info
        build_html_block = f'''
    <div style="margin-top:12px;font-size:13px;color:#57606a;line-height:1.8;">
      仓库 {repo}<br>
      执行状态 {'成功 ✅' if build_status == 'success' else '失败 ❌'}<br>
      提交 SHA {sha}
    </div>'''

    bad_url = f"https://raw.githubusercontent.com/Ethereal-09/rules-hub/main/{platform}/dist/adguard-black.txt"
    ok_url = f"https://raw.githubusercontent.com/Ethereal-09/rules-hub/main/{platform}/dist/adguard-white.txt"

    rows = parse_stats(stats_text)
    fail_rows = [r for r in rows if r[4] != "OK"]

    # 失败源（极简：红色文字列出）
    fail_html = ""
    if fail_rows:
        fs = "、".join(short_name(u) for u, *_ in fail_rows)
        fail_html = f'<div style="margin-top:8px;font-size:13px;color:#cf222e;">拉取失败：{fs}</div>'

    # 完整源列表（简洁）
    all_body = ""
    for url, total, ab, aw, st in rows:
        st_txt = '<span style="color:#1a7f37;">OK</span>' if st == "OK" else '<span style="color:#cf222e;">FAIL</span>'
        all_body += (
            f'<tr>'
            f'<td style="padding:4px 8px;border-bottom:1px solid #eaecef;font-size:13px;word-break:break-all;">{short_name(url)}</td>'
            f'<td style="padding:4px 8px;text-align:right;border-bottom:1px solid #eaecef;font-size:13px;color:#57606a;">{int(total):,}</td>'
            f'<td style="padding:4px 8px;text-align:right;border-bottom:1px solid #eaecef;font-size:13px;color:#57606a;">{int(ab):,}</td>'
            f'<td style="padding:4px 8px;text-align:right;border-bottom:1px solid #eaecef;font-size:13px;color:#57606a;">{int(aw):,}</td>'
            f'<td style="padding:4px 8px;text-align:center;border-bottom:1px solid #eaecef;font-size:13px;">{st_txt}</td>'
            f'</tr>'
        )

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:#ffffff;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#1f2328;">
  <div style="max-width:600px;margin:0 auto;padding:24px;">
    <div style="font-size:20px;font-weight:600;">rules-hub</div>
    <div style="font-size:13px;color:#6a737d;margin-top:4px;">{platform} · {bj} · {status_emoji}</div>

    {build_html_block}

    <div style="border-top:1px solid #eaecef;margin-top:20px;padding-top:16px;">
      <span style="font-size:14px;">黑名单 <strong>{black_n:,}</strong></span>
      <span style="color:#d0d7de;margin:0 10px;">·</span>
      <span style="font-size:14px;">白名单 <strong>{white_n:,}</strong></span>
    </div>

    <div style="margin-top:20px;font-size:14px;font-weight:600;">上游源</div>
    {fail_html}
    <table style="width:100%;border-collapse:collapse;margin-top:8px;font-size:13px;">
      <tr>
        <th style="padding:6px 8px;text-align:left;color:#6a737d;font-weight:500;">源</th>
        <th style="padding:6px 8px;text-align:right;color:#6a737d;font-weight:500;">读取</th>
        <th style="padding:6px 8px;text-align:right;color:#6a737d;font-weight:500;">新增黑</th>
        <th style="padding:6px 8px;text-align:right;color:#6a737d;font-weight:500;">新增白</th>
        <th style="padding:6px 8px;text-align:center;color:#6a737d;font-weight:500;">状态</th>
      </tr>
      {all_body}
    </table>

    <div style="margin-top:20px;font-size:14px;font-weight:600;">订阅地址</div>
    <div style="margin-top:8px;font-size:13px;">
      黑名单 <a href="{bad_url}" style="color:#0969da;text-decoration:none;">{bad_url}</a>
    </div>
    <div style="margin-top:4px;font-size:13px;">
      白名单 <a href="{ok_url}" style="color:#0969da;text-decoration:none;">{ok_url}</a>
    </div>

    <div style="margin-top:24px;padding-top:12px;border-top:1px solid #eaecef;font-size:12px;color:#6a737d;">
      由 rules-hub 自动生成 · 每 8 小时更新
    </div>
  </div>
</body></html>"""
    return html


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

    # 构建信息（可选，来自 GitHub Actions 环境变量）
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    sha = os.environ.get("GITHUB_SHA", "")[:7]
    build_info = (repo, status, sha) if repo and sha else None

    html = build_html(platform, status, stats_text, black_n, white_n, "", build_info)

    msg = MIMEText(html, "html", "utf-8")
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
