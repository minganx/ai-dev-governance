from __future__ import annotations

import unittest

from hooks.check_commit_message import validate_message


class CheckCommitMessageTest(unittest.TestCase):
    def test_accepts_detailed_body_without_fixed_labels(self) -> None:
        message = (
            "fix: 修复登录过期响应\n\n"
            "过期异常此前冒泡为 500，原因是认证中间件未转换异常。\n"
            "本次增加异常映射，验证后接口稳定返回 401。"
        )

        self.assertEqual(validate_message(message), [])

    def test_rejects_missing_body(self) -> None:
        self.assertIn("Commit 必须包含正文。", validate_message("docs: 更新说明\n"))

    def test_rejects_short_body(self) -> None:
        errors = validate_message("fix: 修复问题\n\n修复完成")

        self.assertTrue(any("至少需要" in error for error in errors))

    def test_rejects_placeholder(self) -> None:
        errors = validate_message("feat: 新增能力\n\nTODO：后续补充具体修改内容和验证结果。")

        self.assertTrue(any("占位符" in error for error in errors))

    def test_ignores_git_comment_lines(self) -> None:
        message = "docs: 更新规范\n\n# comment\n"

        self.assertIn("Commit 必须包含正文。", validate_message(message))


if __name__ == "__main__":
    unittest.main()
