"""AdGuard Home 邮件通知的内容测试（脚本位于 .github/notify.py）。"""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]   # 仓库根
spec = importlib.util.spec_from_file_location("agh_notify", ROOT / ".github" / "notify.py")
n = importlib.util.module_from_spec(spec)
spec.loader.exec_module(n)


STATS = """# 合并统计

- 生成时间：2026-10-10 03:00:00
- 上游源：8 个（成功 7，失败 1）
- 黑名单规则：**258,656** 条（去重 1,234）
- 白名单规则：**32** 条（去重 0）

| 上游源 | 读取 | 新增黑 | 新增白 | 状态 |
|---|---|---|---|---|
| https://raw.githubusercontent.com/a/b/ads.txt | 1000 | 900 | 0 | OK |
| https://raw.githubusercontent.com/c/d/broken.txt | 0 | 0 | 0 | FAIL |
"""


class AdGuardNotifyTests(unittest.TestCase):
    def test_parse_summary(self):
        info = n.parse_summary(STATS)
        self.assertIn("8 个", info["sources"])
        self.assertIn("258,656", n.fmt_rule(info["black"]))
        self.assertIn("32", info["white"])

    def test_parse_fail_sources_has_detail(self):
        fails = n.parse_fail_sources(STATS)
        self.assertEqual(len(fails), 1)
        name, total, state = fails[0]
        self.assertIn("broken", name)
        self.assertEqual(total, "0")
        self.assertEqual(state, "FAIL")

    def test_commit_note_rendered(self):
        note = ("fix(adguard): 移除失效白源", ["白源链接置空，改由黑源 @@ 生成"])
        body = n.build_text("adguard", "success", STATS,
                            ("Ethereal-09/rules-hub", "success", "abc1234"),
                            258656, 32, note, "999", "https://github.com/x/y/actions/runs/999")
        self.assertIn("本次改动：", body)
        self.assertIn("fix(adguard): 移除失效白源", body)
        self.assertIn("改由黑源 @@ 生成", body)
        self.assertIn("运行记录：", body)
        self.assertIn("/actions/runs/999", body)

    def test_commit_note_absent_reported(self):
        body = n.build_text("adguard", "success", STATS, None, 1, 1)
        self.assertIn("未能读取提交说明", body)

    def test_failure_body_lists_reason(self):
        body = n.build_text("adguard", "failure", STATS, None, 0, 0)
        self.assertIn("本轮未发布", body)
        self.assertIn("旧版", body)
        self.assertNotIn("258,656", body)
        self.assertNotIn("broken", body)
        self.assertNotIn("黑名单：", body)
        self.assertIn("构建或发布失败", body)
        self.assertNotIn("订阅地址：", body)

    def test_success_body_has_subscription(self):
        body = n.build_text("adguard", "success", STATS, None, 258656, 32)
        self.assertIn("订阅地址：", body)
        self.assertIn("adguard-black.txt", body)
        self.assertIn("adguard-white.txt", body)

    def test_fork_subscription_uses_run_repository(self):
        body = n.build_text("adguard", "success", STATS,
                            ("someone/fork", "success", "abc"))
        self.assertIn("raw.githubusercontent.com/someone/fork/main/adguard/dist/adguard-black.txt", body)
        self.assertNotIn("raw.githubusercontent.com/Ethereal-09/rules-hub", body)

    def test_failure_without_stats_reports_unpublished(self):
        body = n.build_text("adguard", "failure", "", None, 1234, 99)
        self.assertIn("本轮未发布", body)
        self.assertNotIn("1,234", body)
        self.assertNotIn("99 条", body)

    def test_fetch_without_token_is_none(self):
        self.assertIsNone(n.fetch_commit_note("a/b", "sha", ""))
        self.assertIsNone(n.fetch_commit_note("", "sha", "tok"))


if __name__ == "__main__":
    unittest.main()
