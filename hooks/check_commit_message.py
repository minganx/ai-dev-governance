#!/usr/bin/env python3
"""检查 Commit 正文的最低机械质量，不判断业务语义。"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

DEFAULT_MIN_BODY_LENGTH = 20
INVALID_BODIES = {
    "change",
    "changes",
    "fix",
    "fixed",
    "misc",
    "update",
    "updates",
    "wip",
    "代码更新",
    "修改",
    "修复",
    "修复问题",
    "按要求修改",
    "更新",
    "调整",
}
PLACEHOLDER_PATTERN = re.compile(r"<[^>\n]+>|\b(?:TODO|TBD)\b|待补充|占位", re.IGNORECASE)


def _strip_comments(message: str) -> list[str]:
    return [line.rstrip() for line in message.splitlines() if not line.lstrip().startswith("#")]


def _normalize_body(body: str) -> str:
    return re.sub(r"[\W_]+", "", body, flags=re.UNICODE).casefold()


def validate_message(message: str, min_body_length: int = DEFAULT_MIN_BODY_LENGTH) -> list[str]:
    """返回 Commit message 的机械校验错误。"""

    lines = _strip_comments(message)
    if not lines or not lines[0].strip():
        return ["缺少 Commit subject。"]

    body = "\n".join(lines[1:]).strip()
    if not body:
        return ["Commit 必须包含正文。"]

    compact_body = re.sub(r"\s+", "", body)
    errors: list[str] = []
    if len(compact_body) < min_body_length:
        errors.append(f"Commit 正文至少需要 {min_body_length} 个非空白字符，当前为 {len(compact_body)} 个。")
    if _normalize_body(body) in INVALID_BODIES:
        errors.append("Commit 正文过于笼统，必须说明实际问题、修改和结果。")
    if PLACEHOLDER_PATTERN.search(body):
        errors.append("Commit 正文包含 TODO、TBD、待补充或尖括号占位符。")
    return errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("message_file", type=Path, help="Git 提供的 Commit message 文件")
    parser.add_argument(
        "--min-body-length",
        type=int,
        default=DEFAULT_MIN_BODY_LENGTH,
        help=f"正文最少非空白字符数，默认 {DEFAULT_MIN_BODY_LENGTH}",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.min_body_length < 1:
        raise SystemExit("--min-body-length 必须大于 0")

    message = args.message_file.read_text(encoding="utf-8")
    errors = validate_message(message, args.min_body_length)
    if not errors:
        return 0

    print("Commit message 检查失败：", file=sys.stderr)
    for error in errors:
        print(f"- {error}", file=sys.stderr)
    print("正文语义仍须覆盖问题现象、分析原因、修改内容和修改后结果，表达形式不限。", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
