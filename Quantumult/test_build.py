import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("builder", Path(__file__).with_name("build.py"))
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)

BASE = """[general]
server_check_url = https://example.org
[server_remote]
https://example.org/private, enabled=true
[filter_remote]
# https://example.org/comment.list, enabled=true
https://example.org/a.list, tag=A, enabled=true
;https://example.org/disabled.list, enabled=true
https://example.org/off.list, enabled=false
https://example.org/fail.list, enabled=true
https://example.org/private?token=secret, enabled=true
[rewrite_remote]
https://example.org/a.conf, tag=RW, enabled=true
[mitm]
hostname = example.org
"""


class BuilderTests(unittest.TestCase):
    def test_mirror_only_enabled(self):
        fetched = []
        def fetch(url, limit):
            fetched.append(url)
            if "fail" in url:
                raise OSError("offline")
            return b"HOST-SUFFIX,example.org"
        assets = {}
        result, stats = b.process(BASE, fetch, assets)
        self.assertEqual(stats, {"filter": 1, "rewrite": 1, "failed": 1, "skipped": 1})
        self.assertEqual(len(assets), 2)
        self.assertEqual(len(fetched), 3)
        self.assertIn("https://example.org/fail.list, enabled=true", result)
        self.assertIn("https://example.org/off.list, enabled=false", result)
        self.assertIn("https://example.org/private?token=secret", result)
        self.assertIn("[server_remote]\nhttps://example.org/private", result)
        self.assertIn("Quantumult/assets/filter/a-", result)
        self.assertIn("Quantumult/assets/rewrite/a-", result)
        self.assertEqual(len(result.splitlines()), len(BASE.splitlines()))
        self.assertIn(", tag=A, enabled=true\n;https://example.org/disabled.list", result)
        self.assertIn(", tag=RW, enabled=true\n[mitm]", result)

    def test_consecutive_rewrites_and_crlf(self):
        source = "[general]\r\n[rewrite_remote]\r\nhttps://example.org/one.conf, enabled=true\r\nhttps://example.org/two.conf, enabled=true\r\n"
        result, stats = b.process(source, lambda url, limit: b"# rewrite\n", {})
        self.assertEqual(stats["rewrite"], 2)
        self.assertEqual(result.count("\r\n"), 4)
        self.assertEqual(len(result.splitlines()), len(source.splitlines()))
        self.assertIn("enabled=true\r\nhttps://raw.githubusercontent.com/", result)

    def test_reject_bad_base(self):
        with self.assertRaises(ValueError):
            b.process("<html>bad</html>", lambda u, n: b"", {})

    def test_unique_paths_and_safety(self):
        self.assertNotEqual(b.mirror_name("https://a.example/x.list"), b.mirror_name("https://b.example/x.list"))
        self.assertFalse(b.safe_public_url("http://example.org/x.list"))
        self.assertFalse(b.safe_public_url("https://example.org/x?key=abc"))


if __name__ == "__main__":
    unittest.main()
