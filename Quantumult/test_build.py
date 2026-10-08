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
        self.assertEqual(stats, {"filter": 1, "rewrite": 1, "script": 0, "failed": 1, "skipped": 1})
        self.assertEqual(len(assets), 2)
        self.assertEqual(len(fetched), 3)
        self.assertIn("https://example.org/fail.list, enabled=true", result)
        self.assertIn("https://example.org/off.list, enabled=false", result)
        self.assertIn("https://example.org/private?token=secret", result)
        self.assertIn("[server_remote]\nhttps://example.org/private", result)
        self.assertIn("Quantumult/assets/filter/a-", result)
        self.assertIn("Quantumult/assets/rewrite/a-", result)
        self.assertEqual(len(result[result.index("[general]"):].splitlines()), len(BASE.splitlines()))
        self.assertIn(", tag=A, enabled=true\n;https://example.org/disabled.list", result)
        self.assertIn(", tag=RW, enabled=true\n[mitm]", result)

    def test_consecutive_rewrites_and_crlf(self):
        source = "[general]\r\n[rewrite_remote]\r\nhttps://example.org/one.conf, enabled=true\r\nhttps://example.org/two.conf, enabled=true\r\n"
        result, stats = b.process(source, lambda url, limit: b"# rewrite\n", {})
        self.assertEqual(stats["rewrite"], 2)
        self.assertEqual(result.count("\r\n"), 4)
        self.assertEqual(len(result[result.index("[general]"):].splitlines()), len(source.splitlines()))
        self.assertIn("enabled=true\r\nhttps://raw.githubusercontent.com/", result)

    def test_script_dependencies_and_exclusions(self):
        source = """[general]
resource_parser_url=https://example.org/parser.js
profile_img_url=https://example.org/icon.png
[task_local]
event-interaction https://example.org/check.js, tag=Check, enabled=true
;event-interaction https://example.org/old.js
[rewrite_remote]
https://example.org/rewrite.conf, enabled=true
[server_remote]
https://example.org/private.yaml#token=abc, enabled=true
"""
        rewrite = b"""[Rewrite]
^https://ads.example.org url script-response-body https://example.org/logic.js
# ^https://old.example.org url script-response-body https://example.org/disabled.js
^https://www.example.org url 302 https://example.org/redirect.js
[MITM]
hostname=ads.example.org
"""
        seen = []
        def fetch(url, limit):
            seen.append(url)
            return rewrite if url.endswith("rewrite.conf") else b"// script\n"
        assets = {}
        result, stats = b.process(source, fetch, assets)
        self.assertEqual(stats["script"], 3)
        self.assertEqual(len(assets), 4)
        self.assertEqual(len(seen), 4)
        self.assertIn("profile_img_url=https://example.org/icon.png", result)
        self.assertIn("https://example.org/private.yaml#token=abc", result)
        self.assertIn("https://example.org/old.js", result)
        mirrored = next(v.decode() for k, v in assets.items() if k.startswith("rewrite/"))
        self.assertIn("/assets/script/logic-", mirrored)
        self.assertIn("https://example.org/disabled.js", mirrored)
        self.assertIn("https://example.org/redirect.js", mirrored)

    def test_sources_manifest_only_successes(self):
        sources = {}
        def fetch(url, limit):
            if "fail" in url:
                raise OSError("offline")
            return b"# QX resource\n"
        assets = {}
        _, stats = b.process(BASE, fetch, assets, sources)
        doc = b.make_sources_md(sources, stats)
        self.assertEqual(len(sources), 2)
        self.assertIn("assets/filter/a-", doc)
        self.assertIn("assets/rewrite/a-", doc)
        self.assertIn("https://example.org/a.list", doc)
        self.assertNotIn("token=secret", doc)
        self.assertNotIn("fail.list", doc)
        self.assertRegex(doc, r"[0-9a-f]{64}")

    def test_replace_upstream_preamble_only(self):
        preface = "// ==UserScript==\n// @Author @ddgksf2013\n// ==/UserScript==\n# changelog\n; advisory\n\n"
        source = preface + BASE
        output, _ = b.process(source, lambda url, limit: b"# valid\n", {})
        self.assertTrue(output.startswith("# Quantumult X 配置 · Ethereal-09 / rules-hub\n"))
        self.assertNotIn("// @Author @ddgksf2013", output)
        self.assertNotIn("# changelog", output)
        self.assertIn("原底包作者：@ddgksf2013", output)
        self.assertEqual(len(output[output.index("[general]"):].splitlines()), len(BASE.splitlines()))
        self.assertEqual(output.count("[general]"), 1)
        with self.assertRaisesRegex(ValueError, "unexpected active content"):
            b.replace_preamble("danger=true\n[general]\n")

    def test_reject_bad_base(self):
        with self.assertRaises(ValueError):
            b.process("<html>bad</html>", lambda u, n: b"", {})

    def test_unique_paths_and_safety(self):
        self.assertNotEqual(b.mirror_name("https://a.example/x.list"), b.mirror_name("https://b.example/x.list"))
        self.assertFalse(b.safe_public_url("http://example.org/x.list"))
        self.assertFalse(b.safe_public_url("https://example.org/x?key=abc"))


if __name__ == "__main__":
    unittest.main()
