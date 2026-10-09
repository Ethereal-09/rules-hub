import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("adguard_merge", Path(__file__).with_name("merge.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class SafetyTests(unittest.TestCase):
    def test_fail_closed_for_any_failed_or_empty_source(self):
        for status, n in (("FAIL", 100), ("OK", 0)):
            with self.subTest(status=status, n=n):
                with self.assertRaisesRegex(ValueError, "上游"):
                    m.validate_output([("https://example.org", n, n, 0, status)], 220000, 15000)

    def test_fail_closed_for_small_or_shrunk_outputs(self):
        stats = [("https://example.org", 100, 90, 10, "OK")]
        for black, white, previous_black, previous_white in ((5, 1000, 0, 0), (1000, 5, 0, 0), (100000, 15000, 220000, 15000), (220000, 5000, 220000, 15000)):
            with self.subTest(black=black, white=white):
                with self.assertRaises(ValueError):
                    m.validate_output(stats, black, white, previous_black, previous_white)
        m.validate_output(stats, 220000, 15000, 220000, 15000)
        with self.assertRaisesRegex(ValueError, "上游"):
            m.validate_output([("https://cosmetic.example", 100, 0, 0, "OK")], 1000, 10)
        with self.assertRaisesRegex(ValueError, "上游"):
            m.validate_output([("https://comments.example", 20, 0, 0, "OK")], 220000, 15000)
        # Black sources consisting solely of exceptions remain valid.
        m.validate_output([("https://exceptions.example", 20, 0, 20, "OK")], 220000, 15000)
        # White sources may contain non-exception rules by design.
        m.validate_output([("https://white.example", 20, 0, 20, "OK")], 220000, 15000)

    def test_previous_white_count_and_bad_header(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "adguard-white.txt"
            p.write_text("! Title: AdGuard Home 白名单（未筛选混合规则）\n! meta\n@@||a.example^\n@@||b.example^\n", encoding="utf-8")
            self.assertEqual(m.previous_count(str(p)), 2)
            p.write_text("! unexpected\n@@||a.example^\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "头部异常"):
                m.previous_count(str(p))

    def test_personal_domain_label_limit(self):
        self.assertTrue(m.BARE_DOMAIN_RE.fullmatch("a" * 63 + ".example"))
        self.assertFalse(m.BARE_DOMAIN_RE.fullmatch("a" * 64 + ".example"))
        self.assertFalse(m.BARE_DOMAIN_RE.fullmatch("example." + "b" * 64))
        self.assertTrue(m.BARE_DOMAIN_RE.fullmatch("a.example"))


if __name__ == "__main__":
    unittest.main()
