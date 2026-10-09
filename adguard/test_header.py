"""生成文件头的元信息与免责声明测试。"""
import importlib.util
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]

spec = importlib.util.spec_from_file_location("agh_merge", ROOT / "adguard" / "merge.py")
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

spec2 = importlib.util.spec_from_file_location("qx_convert", ROOT / "Quantumult" / "lib" / "convert_ads.py")
c = importlib.util.module_from_spec(spec2)
spec2.loader.exec_module(c)


class HeaderTests(unittest.TestCase):
    def test_adguard_header_has_repo_and_disclaimer(self):
        h = m.file_header("AdGuard Home DNS 专用黑名单", "2026-10-10 03:48:46", "258,653")
        self.assertIn("! Title: AdGuard Home DNS 专用黑名单", h)
        self.assertIn("https://github.com/Ethereal-09/rules-hub", h)
        self.assertIn("! Last modified: 2026-10-10 03:48:46", h)
        self.assertIn("! 规则数: 258,653", h)
        self.assertIn("免责声明", h)
        self.assertIn("SOURCES.md", h)

    def test_adguard_header_all_comment_lines(self):
        h = m.file_header("x", "t", 1)
        for line in h.splitlines():
            if line.strip():
                self.assertTrue(line.startswith("!"), f"非注释行: {line!r}")

    def test_qx_ad_list_header_all_comment_lines(self):
        h = c.ad_list_header(198834)
        for line in h.splitlines():
            if line.strip():
                self.assertTrue(line.startswith("#"), f"非注释行: {line!r}")

    def test_qx_ad_list_header_mentions_sources(self):
        h = c.ad_list_header(198834)
        self.assertIn("SOURCES.md", h)
        self.assertIn("免责声明", h)
        self.assertIn("198,834", h)
        self.assertRegex(h, r"Last modified: \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}")

    def test_header_count_formatting(self):
        self.assertIn("258,653", m.file_header("x", "t", f"{258653:,}"))
        self.assertIn("198,834", c.ad_list_header(198834))


if __name__ == "__main__":
    unittest.main()
