import tempfile
from pathlib import Path
import unittest

from _bootstrap import load

v = load("Quantumult/lib/validate.py", "qx_validate")


class ValidateTests(unittest.TestCase):
    def test_missing_mirror_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "SOURCES.md").write_text("# empty\n")
            conf = root / "QuantumultX.conf"
            conf.write_text("# header\n[general]\nx=1\n[policy]\nx=2\n[rewrite_remote]\nhttps://raw.githubusercontent.com/a/b/main/Quantumult/assets/script/missing.js, tag=x\n[filter_remote]\n")
            with self.assertRaisesRegex(ValueError, "缺文件"):
                v.validate(conf, root)

    def test_valid_minimal_output_and_missing_addition(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "SOURCES.md").write_text("# empty\n")
            conf = root / "QuantumultX.conf"
            conf.write_text("# header\n[general]\nx=1\n[policy]\nstatic=我的组, direct\n[rewrite_remote]\n# none\n[filter_remote]\n" + "# padding\n" * 12)
            self.assertEqual(v.validate(conf, root, ["static=我的组"]), 0)
            with self.assertRaisesRegex(ValueError, "追加项丢失"):
                v.validate(conf, root, ["static=不存在"])


if __name__ == "__main__":
    unittest.main()
