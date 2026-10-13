import json
from pathlib import Path
import tempfile
import unittest

from _bootstrap import load

p = load("Quantumult/lib/overrides.py", "qx_overrides")

BASE = """# top
[general]
dns = x
[policy]
static=香港节点, direct, proxy
static=全球加速, 香港节点, proxy
[rewrite_remote]
https://example.org/a.conf, tag=alpha, enabled=true
[filter_local]
domain-suffix,example.org,direct
"""


class OverridesTests(unittest.TestCase):
    def test_replace_and_remove_preserve_unrelated_upstream(self):
        patches = [
            {"section": "policy", "operation": "replace", "match": "static=香港节点",
             "expected_sha256": p.digest("static=香港节点, direct, proxy"),
             "value": "static=香港节点, proxy, direct"},
            {"section": "rewrite_remote", "operation": "remove", "match": "https://example.org/a.conf",
             "expected_sha256": p.digest("https://example.org/a.conf, tag=alpha, enabled=true")},
        ]
        result = p.apply_patches(BASE, patches)
        self.assertIn("static=香港节点, proxy, direct", result)
        self.assertIn("static=全球加速, 香港节点, proxy", result)
        self.assertNotIn("https://example.org/a.conf", result)

    def test_upstream_modifies_target_then_fail_closed(self):
        patch = {"section": "policy", "operation": "replace", "match": "static=香港节点",
                 "expected_sha256": p.digest("static=香港节点, direct, proxy"),
                 "value": "static=香港节点, proxy"}
        with self.assertRaisesRegex(p.PatchConflict, "上游已更改"):
            p.apply_patches(BASE.replace("direct, proxy", "direct, proxy, auto", 1), [patch])

    def test_missing_or_duplicate_target_fails(self):
        patch = {"section": "policy", "operation": "remove", "match": "static=香港节点",
                 "expected_sha256": p.digest("static=香港节点, direct, proxy")}
        with self.assertRaises(p.PatchConflict):
            p.apply_patches(BASE.replace("static=香港节点", "static=台湾节点"), [patch])
        with self.assertRaises(p.PatchConflict):
            p.apply_patches(BASE.replace("[rewrite_remote]", "static=香港节点, direct, proxy\n[rewrite_remote]"), [patch])

    def test_state_records_no_upstream_line_or_credentials(self):
        state = p.section_state(BASE + "\npassword = SECRET\n")
        result = json.dumps(state)
        self.assertNotIn("SECRET", result)
        self.assertEqual([], p.state_report(state, state))
        self.assertIn("[policy]", "\n".join(p.state_report(p.section_state(BASE), p.section_state(BASE.replace("direct, proxy", "proxy", 1)))))

    def test_upstream_added_duplicate_personal_entry_fails(self):
        from Quantumult.build import process
        with self.assertRaisesRegex(ValueError, "上游新增与个人追加冲突"):
            process(BASE, lambda u, n: b"ok", {}, local_policies=["static=香港节点, proxy, direct"])

    def test_exact_filter_local_rule_can_be_removed(self):
        patch = {"section": "filter_local", "operation": "remove",
                 "match": "domain-suffix,example.org,direct",
                 "expected_sha256": p.digest("domain-suffix,example.org,direct")}
        self.assertNotIn("domain-suffix,example.org,direct", p.apply_patches(BASE, [patch]))

    def test_bad_manifest_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "overrides.json"
            path.write_text(json.dumps([{"section": "policy", "operation": "remove", "match": "x"}]))
            with self.assertRaises(ValueError):
                p.load_patches(path)


if __name__ == "__main__":
    unittest.main()
