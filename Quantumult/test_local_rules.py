import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


lr = load("local_rules")


BASE = """# header
[general]
dns_exclusion_list = x
[rewrite_local]

^https://api\\.base\\.com/ad url reject-200

[rewrite_remote]

# ======= 广告净化 ======= #
https://upstream.example.com/A.conf, tag=A, enabled=true

[server_local]
[mitm]
hostname = api.base.com
"""

ENTRY = "https://raw.githubusercontent.com/ddgksf2013/Rewrite/master/AdBlock/KeepAds.conf, tag=Keep, enabled=true"


class LocalRuleTests(unittest.TestCase):
    def test_load_skips_comments_and_blanks(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "rewrite-local.txt"
            p.write_text("# c\n\nhttps://a/b.conf, tag=x, enabled=true\n; other\n", encoding="utf-8")
            self.assertEqual(lr.load_local_rules(p), ["https://a/b.conf, tag=x, enabled=true"])

    def test_missing_file_returns_empty(self):
        self.assertEqual(lr.load_local_rules(Path("/nonexistent/rewrite-local.txt")), [])

    def test_no_rules_is_noop(self):
        self.assertEqual(lr.inject_local_rules(BASE, [], lambda r: r), BASE)

    def test_append_into_existing_rewrite_remote(self):
        out = lr.inject_local_rules(BASE, [ENTRY], lambda r: r)
        remote = out.split("[rewrite_remote]", 1)[1].split("[server_local]", 1)[0]
        # upstream entry kept, personal entry appended after it, inside the section
        self.assertIn("upstream.example.com/A.conf", remote)
        self.assertIn("KeepAds.conf", remote)
        self.assertLess(remote.index("upstream.example.com"), remote.index("KeepAds.conf"))
        # did not leak into rewrite_local or extra sections
        local = out.split("[rewrite_local]", 1)[1].split("[rewrite_remote]", 1)[0]
        self.assertNotIn("KeepAds.conf", local)

    def test_creates_section_when_absent(self):
        text = "[general]\nx=1\n[mitm]\nhostname = a.com\n"
        out = lr.inject_local_rules(text, [ENTRY], lambda r: r)
        self.assertIn("[rewrite_remote]", out)
        self.assertIn("KeepAds.conf", out)
        self.assertLess(out.index("[rewrite_remote]"), out.index("KeepAds.conf"))

    def test_rewrite_callback_applied(self):
        out = lr.inject_local_rules(BASE, [ENTRY], lambda r: r.replace("ddgksf2013", "MIRROR"))
        self.assertIn("MIRROR", out)
        self.assertNotIn("ddgksf2013", out.split("[rewrite_remote]", 1)[1])


if __name__ == "__main__":
    unittest.main()
