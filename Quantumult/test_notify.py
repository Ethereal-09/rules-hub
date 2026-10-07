import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("qx_notify", Path(__file__).with_name("notify.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class NotificationTests(unittest.TestCase):
    def test_success_body(self):
        body = module.make_message("success", "本次：分流 12、重写 18、脚本引用 45；失败 2、跳过 1。", "Ethereal-09/rules-hub", "1234", "abcdef123456")
        self.assertIn("分流 12、重写 18、脚本引用 45", body)
        self.assertIn("下载失败 2、跳过 1", body)
        self.assertIn("/actions/runs/1234", body)
        self.assertIn("Quantumult/dist/QuantumultX.conf", body)

    def test_failure_body(self):
        body = module.make_message("failure", "", "Ethereal-09/rules-hub", "4567", "deadbeef")
        self.assertIn("构建或发布失败", body)
        self.assertNotIn("配置地址：", body)


if __name__ == "__main__":
    unittest.main()
