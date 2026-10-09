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


pr = load("policy_rules")

BASE = """# header
[general]
dns_exclusion_list = x
[policy]

static=兜底分流, 自动选择, direct

url-latency-benchmark=香港节点, server-tag-regex=(?=.*(港|HK))^((?!(台|日)).)*$

[filter_remote]
https://up.example.com/a.list, tag=a, enabled=true
"""

ENTRY = "url-latency-benchmark=越南节点, server-tag-regex=(?i)^.*\\bVN\\d, check-interval=1200, tolerance=0"


class PolicyRuleTests(unittest.TestCase):
    def test_load_skips_comments_and_blanks(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "policy-local.txt"
            p.write_text("# c\n\nurl-latency-benchmark=A, x=1\n; other\n", encoding="utf-8")
            self.assertEqual(pr.load_local_rules(p), ["url-latency-benchmark=A, x=1"])

    def test_missing_file_returns_empty(self):
        self.assertEqual(pr.load_local_rules(Path("/nonexistent/policy-local.txt")), [])

    def test_no_rules_is_noop(self):
        self.assertEqual(pr.inject_local_policies(BASE, []), BASE)

    def test_append_into_existing_policy(self):
        out = pr.inject_local_policies(BASE, [ENTRY])
        pol = out.split("\n[policy]\n", 1)[1].split("[filter_remote]", 1)[0]
        self.assertIn("越南节点", pol)
        self.assertIn("香港节点", pol)
        # upstream policy kept, personal appended after it
        self.assertLess(pol.index("香港节点"), pol.index("越南节点"))
        # did not leak outside [policy]
        self.assertNotIn("越南节点", out.split("[filter_remote]", 1)[1])

    def test_creates_section_when_absent(self):
        text = "[general]\nx=1\n[mitm]\nhostname = a.com\n"
        out = pr.inject_local_policies(text, [ENTRY])
        self.assertIn("[policy]", out)
        self.assertLess(out.index("[policy]"), out.index("越南节点"))

    def test_rewrite_callback_applied(self):
        out = pr.inject_local_policies(BASE, [ENTRY], lambda r: r.replace("越南", "MIRROR"))
        self.assertIn("MIRROR", out)


if __name__ == "__main__":
    unittest.main()
