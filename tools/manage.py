#!/usr/bin/env python3
"""跨平台安装、更新、检查并卸载全局 AI 开发规则和通用 Skill。"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CONFIG_ROOT = REPOSITORY_ROOT / "config" / "agents"
CLAUDE_ENTRY = REPOSITORY_ROOT / "config" / "tool-entries" / "claude" / "CLAUDE.md"
GIT_IGNORE_SOURCE = REPOSITORY_ROOT / "config" / "git" / "gitignore_global"
RUFF_CONFIG_SOURCE = REPOSITORY_ROOT / "config" / "ruff" / "ruff.toml"
SUPPORTED_AGENTS = ("claude", "codex", "cursor", "pi")
PI_CURSOR_PACKAGE = "npm:@rahularya01/pi-cursor"
AGENT_SKILL_DIRS = {
    "claude": Path(".claude") / "skills",
    "codex": Path(".codex") / "skills",
    "cursor": Path(".cursor") / "skills",
    "pi": Path(".agents") / "skills",
}


@dataclass(frozen=True)
class ManagedFile:
    source: Path
    target: Path


def _ruff_config_target(home: Path) -> Path:
    if os.name == "nt":
        return home / "AppData" / "Roaming" / "ruff" / "ruff.toml"
    return home / ".config" / "ruff" / "ruff.toml"


def _skill_files(skills_root: Path) -> list[tuple[str, Path, Path]]:
    files: list[tuple[str, Path, Path]] = []
    for skill_entry in sorted(skills_root.glob("*/SKILL.md")):
        skill_root = skill_entry.parent
        for source in sorted(path for path in skill_root.rglob("*") if path.is_file()):
            files.append((skill_root.name, source, source.relative_to(skill_root)))
    return files


def managed_files(
    home: Path,
    agents: Optional[tuple[str, ...]] = None,
    *,
    include_shared: bool = True,
) -> list[ManagedFile]:
    selected_agents = agents or SUPPORTED_AGENTS
    files: list[ManagedFile] = []
    if include_shared:
        files.extend(
            [
                ManagedFile(
                    CONFIG_ROOT / "AGENTS.md",
                    home / ".config" / "agents" / "AGENTS.md",
                ),
                ManagedFile(GIT_IGNORE_SOURCE, home / ".gitignore_global"),
                ManagedFile(RUFF_CONFIG_SOURCE, _ruff_config_target(home)),
            ]
        )

    if "claude" in selected_agents:
        files.append(ManagedFile(CLAUDE_ENTRY, home / ".claude" / "CLAUDE.md"))
    if "codex" in selected_agents:
        files.append(
            ManagedFile(CONFIG_ROOT / "AGENTS.md", home / ".codex" / "AGENTS.md")
        )
    if "pi" in selected_agents:
        files.append(
            ManagedFile(CONFIG_ROOT / "AGENTS.md", home / ".pi" / "agent" / "AGENTS.md")
        )

    for skill_name, source, relative_path in _skill_files(CONFIG_ROOT / "skills"):
        if include_shared:
            files.append(
                ManagedFile(
                    source,
                    home
                    / ".config"
                    / "agents"
                    / "skills"
                    / skill_name
                    / relative_path,
                )
            )
        for agent in selected_agents:
            skill_dir = AGENT_SKILL_DIRS[agent]
            files.append(
                ManagedFile(source, home / skill_dir / skill_name / relative_path)
            )
    return files


def _same_content(source: Path, target: Path) -> bool:
    return target.is_file() and source.read_bytes() == target.read_bytes()


def _atomic_copy(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(source.read_bytes())
    os.replace(temporary, target)


def install(
    home: Path,
    force: bool,
    agents: Optional[tuple[str, ...]] = None,
) -> int:
    files = managed_files(home, agents)
    conflicts = [
        item.target
        for item in files
        if item.target.exists() and not _same_content(item.source, item.target)
    ]
    if conflicts and not force:
        print("存在不同内容，未覆盖。确认后使用 install --force：", file=sys.stderr)
        for target in conflicts:
            print(f"- {target}", file=sys.stderr)
        return 2

    changed = 0
    for item in files:
        if _same_content(item.source, item.target):
            continue
        _atomic_copy(item.source, item.target)
        changed += 1
        print(f"installed {item.target}")
    print(f"完成：更新 {changed} 个文件。")
    return 0


def update(
    home: Path,
    force: bool,
    agents: Optional[tuple[str, ...]] = None,
) -> int:
    conflicts: list[Path] = []
    changed = 0
    for item in managed_files(home, agents):
        if _same_content(item.source, item.target):
            continue
        if item.target.exists() and not force:
            conflicts.append(item.target)
            continue
        _atomic_copy(item.source, item.target)
        changed += 1
        print(f"updated {item.target}")

    print(f"完成：更新 {changed} 个文件。")
    if not conflicts:
        return 0

    print("以下文件存在本地差异，已保留。确认后使用 update --force：", file=sys.stderr)
    for target in conflicts:
        print(f"- {target}", file=sys.stderr)
    return 2


def check(home: Path, agents: Optional[tuple[str, ...]] = None) -> int:
    drifted = [
        item.target
        for item in managed_files(home, agents)
        if not _same_content(item.source, item.target)
    ]
    if not drifted:
        print("全局规则和 Skill 与治理仓库一致。")
        return 0

    print("发现缺失或漂移：", file=sys.stderr)
    for target in drifted:
        print(f"- {target}", file=sys.stderr)
    return 1


def manage_third_party_packages(
    home: Path,
    command: str,
    agents: Optional[tuple[str, ...]] = None,
) -> int:
    selected_agents = agents or SUPPORTED_AGENTS
    if "pi" not in selected_agents:
        return 0

    pi = shutil.which("pi")
    if pi is None:
        print("未找到 Pi CLI，无法管理 pi-cursor Package。", file=sys.stderr)
        return 1

    environment = os.environ.copy()
    environment["PI_CODING_AGENT_DIR"] = str(home / ".pi" / "agent")
    listed = subprocess.run(
        [pi, "list"],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    if listed.returncode != 0:
        print(listed.stderr, file=sys.stderr, end="")
        return listed.returncode

    installed = PI_CURSOR_PACKAGE in listed.stdout
    if command == "check":
        if installed:
            return 0
        print(f"缺少 Pi Package：{PI_CURSOR_PACKAGE}", file=sys.stderr)
        return 1
    if command == "install" and installed:
        return 0
    if command == "update" and not installed:
        command = "install"
    if command == "uninstall":
        if not installed:
            return 0
        package_command = "remove"
    else:
        package_command = command

    result = subprocess.run(
        [pi, package_command, PI_CURSOR_PACKAGE],
        env=environment,
        check=False,
    )
    return result.returncode


def _remove_empty_parents(directory: Path, home: Path) -> None:
    while directory != home:
        try:
            directory.rmdir()
        except OSError:
            return
        directory = directory.parent


def uninstall(
    home: Path,
    force: bool,
    agents: Optional[tuple[str, ...]] = None,
) -> int:
    include_shared = agents is None
    files = managed_files(home, agents, include_shared=include_shared)
    conflicts = [
        item.target
        for item in files
        if item.target.exists() and not _same_content(item.source, item.target)
    ]
    if conflicts and not force:
        print("存在本地修改，未删除。确认后使用 uninstall --force：", file=sys.stderr)
        for target in conflicts:
            print(f"- {target}", file=sys.stderr)
        return 2

    removed = 0
    for item in files:
        if not item.target.is_file():
            continue
        item.target.unlink()
        _remove_empty_parents(item.target.parent, home)
        removed += 1
        print(f"removed {item.target}")
    print(f"完成：删除 {removed} 个文件。")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("install", "update", "check", "uninstall"))
    parser.add_argument("--force", action="store_true", help="覆盖或删除存在本地修改的受管文件")
    parser.add_argument(
        "--agent",
        action="append",
        choices=SUPPORTED_AGENTS,
        dest="agents",
        help="只管理指定 Agent，可重复使用；默认管理全部 Agent",
    )
    parser.add_argument("--home", type=Path, default=Path.home(), help=argparse.SUPPRESS)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    home = args.home.expanduser().resolve()
    agents = tuple(dict.fromkeys(args.agents)) if args.agents else None
    if args.command == "install":
        result = install(home, args.force, agents)
        if result != 0:
            return result
        return manage_third_party_packages(home, "install", agents)
    if args.command == "update":
        result = update(home, args.force, agents)
        package_result = manage_third_party_packages(home, "update", agents)
        return result or package_result
    if args.command == "uninstall":
        result = uninstall(home, args.force, agents)
        if result != 0:
            return result
        return manage_third_party_packages(home, "uninstall", agents)
    if args.force:
        raise SystemExit("check 不支持 --force")
    result = check(home, agents)
    package_result = manage_third_party_packages(home, "check", agents)
    return result or package_result


if __name__ == "__main__":
    sys.exit(main())
