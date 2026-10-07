#!/usr/bin/env python3
"""Email a concise Quantumult X build/publish result via existing SMTP secrets."""
import os
from pathlib import Path
import re
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage


def make_message(status, manifest, repo, run_id, revision):
    state = "成功" if status == "success" else "失败"
    now = datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M")
    source = re.search(r"本次：分流 (\d+)、重写 (\d+)、脚本引用 (\d+)；失败 (\d+)、跳过 (\d+)", manifest)
    lines = [f"Quantumult X 构建与发布：{state}", f"北京时间：{now}",
             f"仓库：{repo}", f"运行记录：https://github.com/{repo}/actions/runs/{run_id}",
             f"触发提交：{revision[:12]}"]
    if status == "success":
        if source:
            lines.append("本次镜像：分流 {}、重写 {}、脚本引用 {}；下载失败 {}、跳过 {}".format(*source.groups()))
        lines.extend(["", "配置地址：", f"https://raw.githubusercontent.com/{repo}/main/Quantumult/dist/QuantumultX.conf",
                      "镜像来源：", f"https://github.com/{repo}/blob/main/Quantumult/SOURCES.md"])
    else:
        lines.extend(["", "构建或发布失败，请打开运行记录查看失败步骤；不要把旧配置误认为已更新。"])
    return "\n".join(lines)


def main():
    user = os.environ.get("SMTP_USER", "")
    password = os.environ.get("SMTP_PASS", "")
    recipient = os.environ.get("SMTP_TO", "")
    if not (user and password and recipient):
        print("未配置 SMTP_USER / SMTP_PASS / SMTP_TO，跳过 QX 邮件通知")
        return
    status = os.environ.get("BUILD_STATUS", "failure")
    repo = os.environ.get("GITHUB_REPOSITORY", "Ethereal-09/rules-hub")
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    revision = os.environ.get("GITHUB_SHA", "")
    path = Path("Quantumult/SOURCES.md")
    manifest = path.read_text(encoding="utf-8") if path.exists() else ""
    message = EmailMessage()
    message["Subject"] = f"rules-hub Quantumult X {'✅ 构建成功' if status == 'success' else '❌ 构建失败'}"
    message["From"] = user
    message["To"] = recipient
    message.set_content(make_message(status, manifest, repo, run_id, revision))
    with smtplib.SMTP_SSL("smtp.163.com", 465, timeout=30) as server:
        server.login(user, password)
        server.send_message(message)
    print("QX 邮件通知已发送")


if __name__ == "__main__":
    main()
