#!/usr/bin/env python3
"""跨平台安装并检查全局 AI 开发规则和通用 Skill。"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CONFIG_ROOT = REPOSITORY_ROOT / "config" / "agents"
CLAUDE_ENTRY = REPOSITORY_ROOT / "config" / "tool-entries" / "claude" / "CLAUDE.md"
GIT_IGNORE_SOURCE = REPOSITORY_ROOT / "config" / "git" / "gitignore_global"
RUFF_CONFIG_SOURCE = REPOSITORY_ROOT / "config" / "ruff" / "ruff.toml"
TOOL_SKILL_DIRS = (
    Path(".agents") / "skills",
    Path(".claude") / "skills",
    Path(".codex") / "skills",
    Path(".cursor") / "skills",
)


@dataclass(frozen=True)
class ManagedFile:
    source: Path
    target: Path


def _ruff_config_target(home: Path) -> Path:
    if os.name == "nt":
        return home / "AppData" / "Roaming" / "ruff" / "ruff.toml"
    return home / ".config" / "ruff" / "ruff.toml"


def managed_files(home: Path) -> list[ManagedFile]:
    files = [
        ManagedFile(CONFIG_ROOT / "AGENTS.md", home / ".config" / "agents" / "AGENTS.md"),
        ManagedFile(CONFIG_ROOT / "AGENTS.md", home / ".codex" / "AGENTS.md"),
        ManagedFile(CLAUDE_ENTRY, home / ".claude" / "CLAUDE.md"),
        ManagedFile(GIT_IGNORE_SOURCE, home / ".gitignore_global"),
        ManagedFile(RUFF_CONFIG_SOURCE, _ruff_config_target(home)),
    ]
    skill_sources = sorted((CONFIG_ROOT / "skills").glob("*/SKILL.md"))
    for source in skill_sources:
        skill_name = source.parent.name
        files.append(
            ManagedFile(
                source,
                home / ".config" / "agents" / "skills" / skill_name / "SKILL.md",
            )
        )
        for tool_dir in TOOL_SKILL_DIRS:
            files.append(ManagedFile(source, home / tool_dir / skill_name / "SKILL.md"))
    return files


def _same_content(source: Path, target: Path) -> bool:
    return target.is_file() and source.read_bytes() == target.read_bytes()


def _atomic_copy(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(source.read_bytes())
    os.replace(temporary, target)


def install(home: Path, force: bool) -> int:
    conflicts = [
        item.target
        for item in managed_files(home)
        if item.target.exists() and not _same_content(item.source, item.target)
    ]
    if conflicts and not force:
        print("存在不同内容，未覆盖。确认后使用 install --force：", file=sys.stderr)
        for target in conflicts:
            print(f"- {target}", file=sys.stderr)
        return 2

    changed = 0
    for item in managed_files(home):
        if _same_content(item.source, item.target):
            continue
        _atomic_copy(item.source, item.target)
        changed += 1
        print(f"installed {item.target}")
    print(f"完成：更新 {changed} 个文件。")
    return 0


def check(home: Path) -> int:
    drifted = [item.target for item in managed_files(home) if not _same_content(item.source, item.target)]
    if not drifted:
        print("全局规则和 Skill 与治理仓库一致。")
        return 0

    print("发现缺失或漂移：", file=sys.stderr)
    for target in drifted:
        print(f"- {target}", file=sys.stderr)
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("install", "check"))
    parser.add_argument("--force", action="store_true", help="覆盖治理仓库管理的同名文件")
    parser.add_argument("--home", type=Path, default=Path.home(), help=argparse.SUPPRESS)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    home = args.home.expanduser().resolve()
    if args.command == "install":
        return install(home, args.force)
    if args.force:
        raise SystemExit("check 不支持 --force")
    return check(home)


if __name__ == "__main__":
    sys.exit(main())
