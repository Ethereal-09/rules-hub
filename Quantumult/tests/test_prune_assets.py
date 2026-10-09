import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest import mock

from _bootstrap import load

pa = load("Quantumult/lib/prune_assets.py", "prune_assets")


class PruneTests(unittest.TestCase):
    def _setup(self, d):
        assets = Path(d) / "assets"
        for cat in ("filter", "rewrite", "script"):
            (assets / cat).mkdir(parents=True)
        dist = Path(d) / "dist"
        dist.mkdir()
        (dist / "QuantumultX.conf").write_text(
            "https://raw.githubusercontent.com/x/rules-hub/main/Quantumult/assets/script/keep.js\n",
            encoding="utf-8")
        (Path(d) / "SOURCES.md").write_text("", encoding="utf-8")
        return assets

    def test_removes_unreferenced_and_old(self):
        with tempfile.TemporaryDirectory() as d:
            assets = self._setup(d)
            old = assets / "script" / "gone.js"
            old.write_text("x", encoding="utf-8")
            stale = time.time() - 60 * 86400
            os.utime(old, (stale, stale))
            keep = assets / "script" / "keep.js"
            keep.write_text("y", encoding="utf-8")
            os.utime(keep, (stale, stale))
            with mock.patch.object(pa, "ASSETS", assets), mock.patch.object(pa, "ROOT", Path(d)):
                removed, kept = pa.prune(30)
            self.assertEqual(removed, 1)
            self.assertEqual(kept, 1)
            self.assertFalse(old.exists())
            self.assertTrue(keep.exists())

    def test_recent_unreferenced_is_kept(self):
        with tempfile.TemporaryDirectory() as d:
            assets = self._setup(d)
            recent = assets / "rewrite" / "recent.conf"
            recent.write_text("x", encoding="utf-8")
            with mock.patch.object(pa, "ASSETS", assets), mock.patch.object(pa, "ROOT", Path(d)):
                removed, kept = pa.prune(30)
            self.assertEqual(removed, 0)
            self.assertTrue(recent.exists())

    def test_old_git_asset_removed_despite_recent_checkout_mtime(self):
        with tempfile.TemporaryDirectory() as d:
            assets = self._setup(d)
            old = assets / "script" / "orphan.js"
            old.write_text("x", encoding="utf-8")
            with (mock.patch.object(pa, "ASSETS", assets),
                  mock.patch.object(pa, "ROOT", Path(d)),
                  mock.patch.object(pa, "last_change_time", return_value=time.time() - 60 * 86400)):
                removed, _ = pa.prune(30)
            self.assertEqual(removed, 1)
            self.assertFalse(old.exists())

    def test_missing_assets_dir_is_noop(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.object(pa, "ASSETS", Path(d) / "nope"):
                removed, kept = pa.prune(30)
            self.assertEqual(removed, 0)


if __name__ == "__main__":
    unittest.main()
