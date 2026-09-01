#!/usr/bin/env python3
"""使用设备本地 API Key 启动 Context7 官方 MCP Server。"""

from __future__ import annotations

import argparse
import os
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--secret-file", type=Path, required=True)
    args = parser.parse_args()

    if not args.secret_file.is_file():
        raise SystemExit(f"缺少 Context7 API Key 文件：{args.secret_file}")
    api_key = args.secret_file.read_text(encoding="utf-8").strip()
    if not api_key:
        raise SystemExit(f"Context7 API Key 文件为空：{args.secret_file}")

    environment = os.environ.copy()
    environment["CONTEXT7_API_KEY"] = api_key
    os.execvpe(
        "npx",
        ["npx", "-y", "@upstash/context7-mcp"],
        environment,
    )


if __name__ == "__main__":
    main()
