import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("convert_ads", Path(__file__).with_name("convert_ads.py"))
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)


class ConvertAdsTests(unittest.TestCase):
    def test_safe_rules_and_exceptions(self):
        black = """! meta
||ads.example.com^
||sub.ads.example.com^
||tracker.test^
||example.org^$important
example.com##.banner
/ads[0-9]+/
@@||tracker.test^
||safe.example.net^
"""
        white = """@@||example.com^
@@||ads.example.com^
@@||safe.example.net^$important
"""
        rules, stats = c.convert(black, white)
        self.assertEqual(rules, ["HOST-SUFFIX,example.org,REJECT", "HOST-SUFFIX,safe.example.net,REJECT"])
        self.assertEqual(stats["excluded"], 3)
        self.assertEqual(stats["important_downgraded"], 1)
        self.assertEqual(stats["black_unsupported"], 2)
        self.assertEqual(stats["white_ambiguous"], 1)

    def test_domain_validation(self):
        self.assertEqual(c.parse_domain("||EXAMPLE.COM^"), "example.com")
        for rule in ["||*.example.com^", "||example.com^$third-party", "a/b", "||example.com", "||foo..com^"]:
            self.assertIsNone(c.parse_domain(rule))

    def test_important_only_not_other_modifiers(self):
        black = "||ads.example.com^$important\n||bad.example.org^$important,third-party\n||ok.example.net^$third-party\n"
        rules, stats = c.convert(black, "")
        self.assertEqual(rules, ["HOST-SUFFIX,ads.example.com,REJECT"])
        self.assertEqual(stats["important_downgraded"], 1)
        self.assertEqual(stats["black_unsupported"], 2)

    def test_no_rules_refuses_publish(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "b").write_text("/complex-rule/\n")
            (root / "w").write_text("@@||example.com^\n")
            import sys
            previous = sys.argv
            try:
                sys.argv = ["convert_ads.py", "--black", str(root / "b"), "--white", str(root / "w"), "--output", str(root / "out")]
                with self.assertRaises(ValueError):
                    c.main()
            finally:
                sys.argv = previous
            self.assertFalse((root / "out").exists())


if __name__ == "__main__":
    unittest.main()
