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
  SMTP_PASS  163 授权码（客户端授权密码）
  SMTP_TO    收件邮箱
"""
import os
import sys
import smtplib
import re
from email.mime.text import MIMEText
from email.header import Header
from datetime import datetime, timezone, timedelta

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


def build_html(platform, status, stats_text, black_n, white_n, ts):
    bj = (datetime.now(timezone.utc) + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M")

    # 状态标题
    if status == "success":
        status_badge = '<span style="color:#16a34a;">✅ 合并成功</span>'
    else:
        status_badge = '<span style="color:#dc2626;">❌ 合并失败</span>'

    bad_url = f"https://raw.githubusercontent.com/Ethereal-09/rules-hub/main/{platform}/dist/adguard-black.txt"
    ok_url = f"https://raw.githubusercontent.com/Ethereal-09/rules-hub/main/{platform}/dist/adguard-white.txt"

    # 源统计表 HTML
    rows_html = ""
    for url, total, ab, aw, st in parse_stats(stats_text):
        st_color = "#16a34a" if st == "OK" else "#dc2626"
        rows_html += (
            f'<tr><td style="padding:6px 10px;border-bottom:1px solid #e5e7eb;'
            f'font-size:12px;color:#4b5563;word-break:break-all;">{url}</td>'
            f'<td style="padding:6px 10px;text-align:center;border-bottom:1px solid #e5e7eb;font-size:12px;">{total}</td>'
            f'<td style="padding:6px 10px;text-align:center;border-bottom:1px solid #e5e7eb;font-size:12px;">{ab}</td>'
            f'<td style="padding:6px 10px;text-align:center;border-bottom:1px solid #e5e7eb;font-size:12px;">{aw}</td>'
            f'<td style="padding:6px 10px;text-align:center;border-bottom:1px solid #e5e7eb;'
            f'font-size:12px;color:{st_color};font-weight:600;">{st}</td></tr>'
        )

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="margin:0;padding:20px;background:#f3f4f6;font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;">
  <div style="max-width:560px;margin:0 auto;background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.1);">
    <div style="background:#111827;color:#fff;padding:18px 24px;">
      <div style="font-size:18px;font-weight:700;">Rules Hub · {platform}</div>
      <div style="font-size:13px;color:#9ca3af;margin-top:4px;">{status_badge} &nbsp;·&nbsp; {bj}（北京时间）</div>
    </div>
    <div style="padding:24px;">
      <table style="width:100%;border-spacing:12px;">
        <tr>
          <td style="background:#eff6ff;border-radius:10px;padding:16px;text-align:center;width:50%;">
            <div style="font-size:12px;color:#6b7280;">黑名单（拦截）</div>
            <div style="font-size:28px;font-weight:800;color:#1e40af;">{black_n:,}</div>
          </td>
          <td style="background:#f0fdf4;border-radius:10px;padding:16px;text-align:center;width:50%;">
            <div style="font-size:12px;color:#6b7280;">白名单（放行）</div>
            <div style="font-size:28px;font-weight:800;color:#15803d;">{white_n:,}</div>
          </td>
        </tr>
      </table>

      <div style="margin-top:20px;">
        <div style="font-size:14px;font-weight:700;color:#111827;margin-bottom:8px;">上游源统计</div>
        <table style="width:100%;border-collapse:collapse;background:#fafafa;border-radius:8px;overflow:hidden;">
          <tr style="background:#f3f4f6;">
            <th style="padding:8px 10px;text-align:left;font-size:12px;color:#6b7280;">上游源</th>
            <th style="padding:8px 10px;font-size:12px;color:#6b7280;">读取</th>
            <th style="padding:8px 10px;font-size:12px;color:#6b7280;">新增黑</th>
            <th style="padding:8px 10px;font-size:12px;color:#6b7280;">新增白</th>
            <th style="padding:8px 10px;font-size:12px;color:#6b7280;">状态</th>
          </tr>
          {rows_html}
        </table>
      </div>

      <div style="margin-top:24px;padding:16px;background:#f9fafb;border-radius:10px;">
        <div style="font-size:13px;font-weight:700;color:#111827;margin-bottom:8px;">订阅地址</div>
        <div style="font-size:13px;margin-bottom:6px;">黑名单：<a href="{bad_url}" style="color:#2563eb;">{bad_url}</a></div>
        <div style="font-size:13px;">白名单：<a href="{ok_url}" style="color:#2563eb;">{ok_url}</a></div>
      </div>
    </div>
    <div style="padding:14px 24px;background:#f9fafb;color:#9ca3af;font-size:11px;text-align:center;">
      rules-hub 自动生成 · 每 8 小时更新
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

    html = build_html(platform, status, stats_text, black_n, white_n, "")

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
