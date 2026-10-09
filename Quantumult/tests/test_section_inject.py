import tempfile
from pathlib import Path
import unittest

from _bootstrap import load

si = load("Quantumult/lib/section_inject.py", "section_inject")


BASE = """# header
[general]
dns_exclusion_list = x
[policy]

static=兜底分流, 自动选择, direct

url-latency-benchmark=香港节点, server-tag-regex=(?=.*HK).*$

[rewrite_remote]

https://up.example.com/A.conf, tag=A, enabled=true

[server_local]
[mitm]
hostname = a.com
"""

REWRITE = "https://raw.githubusercontent.com/ddgksf2013/Rewrite/master/AdBlock/KeepAds.conf, tag=Keep, enabled=true"
POLICY = "url-latency-benchmark=其他节点, server-tag-regex=(?i)VN, check-interval=1200, tolerance=0"


class SectionInjectTests(unittest.TestCase):
    def test_load_skips_comments_and_blanks(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "x.txt"
            p.write_text("# c\n\nreal-line\n; other\n// nope\n", encoding="utf-8")
            self.assertEqual(si.load_entries(p), ["real-line"])

    def test_missing_file_returns_empty(self):
        self.assertEqual(si.load_entries(Path("/nonexistent/x.txt")), [])

    def test_no_entries_is_noop(self):
        self.assertEqual(si.inject_entries(BASE, "policy", [], "banner"), BASE)

    def test_append_rewrite_remote(self):
        out = si.inject_entries(BASE, "rewrite_remote", [REWRITE], "个人追加")
        seg = out.split("\n[rewrite_remote]\n", 1)[1].split("[server_local]", 1)[0]
        self.assertIn("KeepAds.conf", seg)
        self.assertIn("up.example.com/A.conf", seg)
        self.assertLess(seg.index("up.example.com"), seg.index("KeepAds.conf"))

    def test_append_policy_section(self):
        out = si.inject_entries(BASE, "policy", [POLICY], "个人追加策略组")
        seg = out.split("\n[policy]\n", 1)[1].split("[rewrite_remote]", 1)[0]
        self.assertIn("其他节点", seg)
        self.assertIn("香港节点", seg)
        self.assertLess(seg.index("香港节点"), seg.index("其他节点"))

    def test_two_sections_do_not_cross_contaminate(self):
        out = si.inject_entries(BASE, "rewrite_remote", [REWRITE], "个人追加")
        out = si.inject_entries(out, "policy", [POLICY], "个人追加策略组")
        pol = out.split("\n[policy]\n", 1)[1].split("[rewrite_remote]", 1)[0]
        rew = out.split("\n[rewrite_remote]\n", 1)[1].split("[server_local]", 1)[0]
        self.assertNotIn("KeepAds", pol)
        self.assertNotIn("其他节点", rew)

    def test_creates_missing_section(self):
        text = "[general]\nx=1\n[mitm]\nhostname = a.com\n"
        out = si.inject_entries(text, "policy", [POLICY], "banner")
        self.assertIn("[policy]", out)
        self.assertLess(out.index("[policy]"), out.index("其他节点"))

    def test_transform_applied(self):
        out = si.inject_entries(BASE, "rewrite_remote", [REWRITE], "b",
                                transform=lambda r: r.replace("ddgksf2013", "MIRROR"))
        self.assertIn("MIRROR", out)

    def test_crlf_preserved(self):
        text = "[general]\r\nx=1\r\n[policy]\r\n\r\nurl-latency-benchmark=A, x=1\r\n\r\n[mitm]\r\n"
        out = si.inject_entries(text, "policy", [POLICY], "banner")
        seg = out.split("[policy]\r\n", 1)[1].split("[mitm]", 1)[0]
        self.assertIn("其他节点", seg)
        self.assertLess(seg.index("url-latency-benchmark=A"), seg.index("其他节点"))


if __name__ == "__main__":
    unittest.main()
