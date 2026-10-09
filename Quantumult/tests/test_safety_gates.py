import unittest

from _bootstrap import load

b = load("Quantumult/build.py", "qx_build")


def stats(failed, filt=0, rew=0, script=0):
    return {"filter": filt, "rewrite": rew, "script": script,
            "failed": failed, "skipped": 0}


class FailureBudgetTests(unittest.TestCase):
    def test_small_failure_count_passes(self):
        b.check_failure_budget(stats(3, filt=20, rew=50, script=200))

    def test_high_ratio_refuses(self):
        with self.assertRaises(ValueError) as ctx:
            b.check_failure_budget(stats(40, filt=12, rew=35, script=196))
        self.assertIn("拒绝发布", str(ctx.exception))

    def test_zero_total_refuses(self):
        with self.assertRaises(ValueError):
            b.check_failure_budget(stats(20))

    def test_count_below_max_but_ratio_high(self):
        with self.assertRaises(ValueError):
            b.check_failure_budget(stats(2, filt=1, rew=1, script=1))

    def test_count_above_max_even_if_ratio_low(self):
        with self.assertRaises(ValueError):
            b.check_failure_budget(stats(9, script=1000))


class PublicUrlTests(unittest.TestCase):
    def test_plain_https_ok(self):
        self.assertTrue(b.safe_public_url("https://example.com/a.conf"))

    def test_raw_true_query_ok(self):
        self.assertTrue(b.safe_public_url("https://example.com/a.conf?raw=true"))

    def test_credential_query_rejected(self):
        self.assertFalse(b.safe_public_url("https://example.com/a.conf?token=abc"))
        self.assertFalse(b.safe_public_url("https://example.com/a.conf?key=x&raw=true"))
        self.assertFalse(b.safe_public_url("https://example.com/a.conf?sig=PRIVATEVALUE"))

    def test_sensitive_path_rejected(self):
        self.assertFalse(b.safe_public_url("https://example.com/subscription/x.conf"))

    def test_http_and_credentials_rejected(self):
        self.assertFalse(b.safe_public_url("http://example.com/a.conf"))
        self.assertFalse(b.safe_public_url("https://u:p@example.com/a.conf"))

    def test_fragment_rejected(self):
        self.assertFalse(b.safe_public_url("https://example.com/a.conf#frag"))


class ManifestTests(unittest.TestCase):
    def test_failures_listed(self):
        md = b.make_sources_md(
            {"script/a.js": ("https://up/a.js", "deadbeef")},
            stats(1, script=1),
            ["script\thttps://up/b.js\tURLError: timed out"],
        )
        self.assertIn("未能镜像", md)
        self.assertIn("https://up/b.js", md)
        self.assertIn("timed out", md)
        self.assertIn("## 成功镜像", md)

    def test_no_failure_section_when_clean(self):
        md = b.make_sources_md({}, stats(0), [])
        self.assertNotIn("未能镜像", md)


if __name__ == "__main__":
    unittest.main()
