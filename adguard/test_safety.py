import importlib.util
from pathlib import Path
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
        m.validate_output([("https://cosmetic.example", 100, 0, 0, "OK")], 1000, 10)


if __name__ == "__main__":
    unittest.main()
