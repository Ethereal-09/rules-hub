"""README 数字同步：表格与徽章都必须更新，缺失则报错而非静默跳过。"""
import importlib.util
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]

spec = importlib.util.spec_from_file_location("agh_merge", ROOT / "adguard" / "merge.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


README = """<div align="center">
[![Blacklist](https://img.shields.io/badge/AdGuard_黑名单-258k-blue?style=flat-square)](#x)
[![Whitelist](https://img.shields.io/badge/AdGuard_白名单-32-green?style=flat-square)](#x)
<sub>上次更新：—</sub>
</div>

| 类型 | 规则数 |
|:---|:---:|
| **黑名单** · 拦截 | — |
| **白名单** · 放行 | — |
"""


class ReadmeSyncTests(unittest.TestCase):
    def _run(self, text, black, white):
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            (repo / "adguard").mkdir()
            (repo / "README.md").write_text(text, encoding="utf-8")
            with mock.patch.object(m, "ROOT", str(repo / "adguard")):
                m.update_readme(black, white, "2026-10-10 04:20:00")
            return (repo / "README.md").read_text(encoding="utf-8")

    def test_table_and_badge_updated(self):
        out = self._run(README, 258653, 32)
        self.assertIn("| **黑名单** · 拦截 | 258,653 |", out)
        self.assertIn("| **白名单** · 放行 | 32 |", out)
        self.assertIn("AdGuard_黑名单-259k-blue", out)   # 258653 -> 259k（四舍五入）
        self.assertIn("AdGuard_白名单-32-green", out)
        self.assertIn("上次更新：2026-10-10 04:20:00", out)

    def test_small_whitelist_stays_plain(self):
        out = self._run(README, 258653, 8)
        self.assertIn("AdGuard_白名单-8-green", out)

    def test_missing_table_row_raises(self):
        broken = README.replace("| **黑名单** · 拦截 | — |", "")
        with self.assertRaises(ValueError):
            self._run(broken, 100, 10)

    def test_missing_badge_raises(self):
        broken = README.replace("AdGuard_黑名单-258k", "Nothing_here")
        with self.assertRaises(ValueError):
            self._run(broken, 100, 10)


if __name__ == "__main__":
    unittest.main()
