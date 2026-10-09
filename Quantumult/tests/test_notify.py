import unittest

from _bootstrap import load

module = load("Quantumult/lib/notify.py", "qx_notify")


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

    def test_commit_note_rendered(self):
        note = ("feat(quantumult): 增加其他节点分组",
                ["将未被区域组覆盖的 9 个国家节点收进一组"])
        body = module.make_message("success", "", "Ethereal-09/rules-hub", "1", "abc", note)
        self.assertIn("本次改动：", body)
        self.assertIn("feat(quantumult): 增加其他节点分组", body)
        self.assertIn("将未被区域组覆盖的 9 个国家节点收进一组", body)

    def test_commit_note_absent_is_reported(self):
        body = module.make_message("success", "", "Ethereal-09/rules-hub", "1", "abc")
        self.assertIn("本次改动：未能读取提交说明", body)

    def test_fetch_commit_note_without_token(self):
        self.assertIsNone(module.fetch_commit_note("a/b", "sha", ""))
        self.assertIsNone(module.fetch_commit_note("", "sha", "tok"))


if __name__ == "__main__":
    unittest.main()
