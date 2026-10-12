#!/usr/bin/env python3
"""跨平台管理 AI 开发规则、Skill、MCP 配置。"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Optional

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CONFIG_ROOT = REPOSITORY_ROOT / "config" / "agents"
CLAUDE_ENTRY = REPOSITORY_ROOT / "config" / "tool-entries" / "claude" / "CLAUDE.md"
GIT_IGNORE_SOURCE = REPOSITORY_ROOT / "config" / "git" / "gitignore_global"
RUFF_CONFIG_SOURCE = REPOSITORY_ROOT / "config" / "ruff" / "ruff.toml"
MCP_CONFIG_SOURCE = REPOSITORY_ROOT / "config" / "mcp" / "servers.json"
CONTEXT7_INSTALL_DOCS = "https://context7.com/docs/resources/all-clients"
SUPPORTED_AGENTS = ("claude", "codex", "cursor")
MCP_AGENTS = ("claude", "codex", "cursor")
RETIRED_MCP_SERVERS = ("codegraph",)
AGENT_SKILL_DIRS = {
    "claude": Path(".claude") / "skills",
    "codex": Path(".codex") / "skills",
    "cursor": Path(".cursor") / "skills",
}


@dataclass(frozen=True)
class ManagedFile:
    source: Path
    target: Path


@dataclass(frozen=True)
class InstallSelection:
    agents: tuple[str, ...]
    skills: tuple[str, ...]
    mcps: tuple[str, ...]
    configs: tuple[str, ...]


def _selection_path(home: Path) -> Path:
    return home / ".config" / "agents" / "install-selection.json"


def _read_selection(home: Path) -> Optional[InstallSelection]:
    path = _selection_path(home)
    if not path.exists():
        return None
    document = json.loads(path.read_text(encoding="utf-8"))
    keys = {"agents", "skills", "mcps", "configs"}
    if not isinstance(document, dict) or set(document) != keys:
        raise ValueError("安装选择必须包含 agents、skills、mcps、configs。")
    if any(not isinstance(values, list) or any(not isinstance(value, str) for value in values)
           for values in document.values()):
        raise ValueError("安装选择的每一项必须是名称列表。")
    selection = InstallSelection(**{key: tuple(value) for key, value in document.items()})
    if any(agent not in SUPPORTED_AGENTS for agent in selection.agents):
        raise ValueError("安装选择包含不支持的 Agent。")
    if any(config not in ("rules", "git", "ruff") for config in selection.configs):
        raise ValueError("安装选择包含不支持的开发工具配置。")
    return selection


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
    selection: Optional[InstallSelection] = None,
) -> list[ManagedFile]:
    selected_agents = (
        agents if agents is not None
        else selection.agents if selection else SUPPORTED_AGENTS
    )
    files: list[ManagedFile] = []
    configs = selection.configs if selection else ("rules", "git", "ruff")
    if include_shared:
        shared = {
            "rules": ManagedFile(
                CONFIG_ROOT / "AGENTS.md", home / ".config" / "agents" / "AGENTS.md"
            ),
            "git": ManagedFile(GIT_IGNORE_SOURCE, home / ".gitignore_global"),
            "ruff": ManagedFile(RUFF_CONFIG_SOURCE, _ruff_config_target(home)),
        }
        files.extend(shared[name] for name in configs)

    if "rules" in configs:
        if "claude" in selected_agents:
            files.append(ManagedFile(CLAUDE_ENTRY, home / ".claude" / "CLAUDE.md"))
        if "codex" in selected_agents:
            files.append(ManagedFile(CONFIG_ROOT / "AGENTS.md", home / ".codex" / "AGENTS.md"))

    for skill_name, source, relative_path in _skill_files(CONFIG_ROOT / "skills"):
        if selection is not None and skill_name not in selection.skills:
            continue
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
    *,
    selection: Optional[InstallSelection] = None,
) -> int:
    files = managed_files(home, agents, selection=selection)
    conflicts = [
        item.target
        for item in files
        if item.target.exists() and not _same_content(item.source, item.target)
    ]
    if conflicts and not force:
        print("存在不同内容，未覆盖。请重新安装并在菜单中选择以仓库内容覆盖：", file=sys.stderr)
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
    *,
    selection: Optional[InstallSelection] = None,
) -> int:
    conflicts: list[Path] = []
    changed = 0
    for item in managed_files(home, agents, selection=selection):
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


def check(
    home: Path, agents: Optional[tuple[str, ...]] = None,
    *, selection: Optional[InstallSelection] = None,
) -> int:
    drifted = [
        item.target
        for item in managed_files(home, agents, selection=selection)
        if not _same_content(item.source, item.target)
    ]
    if not drifted:
        print("全局规则和 Skill 与治理仓库一致。")
        return 0

    print("发现缺失或漂移：", file=sys.stderr)
    for target in drifted:
        print(f"- {target}", file=sys.stderr)
    return 1


def _resolved_mcp_servers(
    agent: str, servers: Optional[tuple[str, ...]] = None,
) -> dict[str, dict[str, Any]]:
    definitions = json.loads(MCP_CONFIG_SOURCE.read_text(encoding="utf-8"))
    return {
        name: {"transport": definition["transport"], "url": definition["url"]}
        for name, definition in definitions.items()
        if agent in definition["agents"] and (servers is None or name in servers)
    }


def _json_mcp_path(home: Path, agent: str) -> Path:
    if agent == "claude":
        return home / ".claude.json"
    if agent == "cursor":
        return home / ".cursor" / "mcp.json"
    raise ValueError(f"不支持 JSON MCP 配置的 Agent：{agent}")


def _read_json_mcp_servers(home: Path, agent: str) -> tuple[dict[str, Any], dict[str, Any]]:
    path = _json_mcp_path(home, agent)
    document = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    return document, document.setdefault("mcpServers", {})


def _normalize_json_mcp(config: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
    if config is None:
        return None
    if "url" in config:
        return {"transport": "http", "url": config["url"]}
    return {
        "transport": "stdio",
        "command": config.get("command"),
        "args": config.get("args", []),
    }


def _write_json(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        delete=False,
    ) as handle:
        temporary = Path(handle.name)
        handle.write(content)
    os.replace(temporary, path)


def _codex_environment(home: Path) -> dict[str, str]:
    environment = os.environ.copy()
    environment["HOME"] = str(home)
    environment["CODEX_HOME"] = str(home / ".codex")
    return environment


def _read_codex_mcp_servers(home: Path) -> tuple[str, dict[str, dict[str, Any]]]:
    codex = shutil.which("codex")
    if codex is None:
        raise RuntimeError("未找到 Codex CLI，无法管理 Codex MCP。")
    result = subprocess.run(
        [codex, "mcp", "list", "--json"],
        env=_codex_environment(home),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "读取 Codex MCP 配置失败。")
    servers: dict[str, dict[str, Any]] = {}
    for item in json.loads(result.stdout):
        transport = item["transport"]
        if transport["type"] == "stdio":
            servers[item["name"]] = {
                "transport": "stdio",
                "command": transport["command"],
                "args": transport.get("args", []),
            }
        else:
            servers[item["name"]] = {
                "transport": "http",
                "url": transport["url"],
            }
    return codex, servers


def _run_codex_mcp_command(
    home: Path,
    codex: str,
    action: str,
    name: str,
    config: Optional[dict[str, Any]] = None,
) -> int:
    command = [codex, "mcp", action, name]
    if action == "add" and config is not None:
        if config["transport"] == "http":
            command.extend(["--url", config["url"]])
        else:
            command.extend(["--", config["command"], *config["args"]])
    return subprocess.run(
        command,
        env=_codex_environment(home),
        check=False,
    ).returncode


def manage_mcp_servers(
    home: Path,
    command: str,
    agents: Optional[tuple[str, ...]] = None,
    *,
    force: bool = False,
    servers: Optional[tuple[str, ...]] = None,
) -> int:
    if servers == ():
        return 0
    selected = tuple(
        agent for agent in (MCP_AGENTS if agents is None else agents)
        if agent in MCP_AGENTS
    )
    if not selected:
        return 0

    if command == "check":
        drifted: list[str] = []
        for agent in selected:
            desired = _resolved_mcp_servers(agent, servers)
            try:
                if agent == "codex":
                    _, current = _read_codex_mcp_servers(home)
                else:
                    _, raw = _read_json_mcp_servers(home, agent)
                    current = {
                        name: _normalize_json_mcp(config)
                        for name, config in raw.items()
                    }
            except (json.JSONDecodeError, OSError, RuntimeError) as error:
                print(error, file=sys.stderr)
                return 1
            for name in RETIRED_MCP_SERVERS:
                if name in current:
                    drifted.append(f"{agent}:{name}（已退役，执行 update 清理）")
            for name, expected in desired.items():
                if current.get(name) != expected:
                    drifted.append(f"{agent}:{name}")
        if drifted:
            print("发现 MCP 配置缺失或漂移：", file=sys.stderr)
            for item in drifted:
                print(f"- {item}", file=sys.stderr)
            return 1
        print("MCP 配置与治理仓库一致。")
        return 0

    if command == "uninstall" and not force:
        conflicts: list[str] = []
        for agent in selected:
            desired = _resolved_mcp_servers(agent, servers)
            try:
                if agent == "codex":
                    _, current = _read_codex_mcp_servers(home)
                else:
                    _, raw = _read_json_mcp_servers(home, agent)
                    current = {
                        name: _normalize_json_mcp(config)
                        for name, config in raw.items()
                    }
            except (json.JSONDecodeError, OSError, RuntimeError) as error:
                print(error, file=sys.stderr)
                return 1
            for name, expected in desired.items():
                actual = current.get(name)
                if actual is not None and actual != expected:
                    conflicts.append(f"{agent}:{name}")
        if conflicts:
            print("以下 MCP 配置存在本地差异，未删除：", file=sys.stderr)
            for item in conflicts:
                print(f"- {item}", file=sys.stderr)
            return 2

    conflicts: list[str] = []
    for agent in selected:
        desired = _resolved_mcp_servers(agent, servers)
        try:
            if agent == "codex":
                codex, current = _read_codex_mcp_servers(home)
                for name in RETIRED_MCP_SERVERS:
                    if name in current:
                        if _run_codex_mcp_command(home, codex, "remove", name) != 0:
                            return 1
                        print(f"removed retired MCP {agent}:{name}")
                for name, expected in desired.items():
                    actual = current.get(name)
                    if command == "uninstall":
                        if actual is None:
                            continue
                        if actual != expected and not force:
                            conflicts.append(f"{agent}:{name}")
                            continue
                        if _run_codex_mcp_command(home, codex, "remove", name) != 0:
                            return 1
                    elif actual != expected:
                        if actual is not None and not force:
                            conflicts.append(f"{agent}:{name}")
                            continue
                        if actual is not None and _run_codex_mcp_command(
                            home, codex, "remove", name
                        ) != 0:
                            return 1
                        if _run_codex_mcp_command(
                            home, codex, "add", name, expected
                        ) != 0:
                            return 1
                continue

            document, raw = _read_json_mcp_servers(home, agent)
            changed = False
            for name in RETIRED_MCP_SERVERS:
                if name in raw:
                    del raw[name]
                    changed = True
                    print(f"removed retired MCP {agent}:{name}")
            for name, expected in desired.items():
                actual = _normalize_json_mcp(raw.get(name))
                if command == "uninstall":
                    if actual is None:
                        continue
                    if actual != expected and not force:
                        conflicts.append(f"{agent}:{name}")
                        continue
                    del raw[name]
                    changed = True
                elif actual != expected:
                    if actual is not None and not force:
                        conflicts.append(f"{agent}:{name}")
                        continue
                    if expected["transport"] == "http":
                        raw[name] = {"url": expected["url"]}
                        raw[name]["type"] = "http"
                    else:
                        raw[name] = {
                            "command": expected["command"],
                            "args": expected["args"],
                        }
                        raw[name]["type"] = "stdio"
                    changed = True
            if changed:
                _write_json(_json_mcp_path(home, agent), document)
        except (json.JSONDecodeError, OSError, RuntimeError) as error:
            print(error, file=sys.stderr)
            return 1

    if conflicts:
        action = "删除" if command == "uninstall" else "覆盖"
        print(f"以下 MCP 配置存在本地差异，未{action}：", file=sys.stderr)
        for item in conflicts:
            print(f"- {item}", file=sys.stderr)
        return 2
    return 0


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
    *,
    selection: Optional[InstallSelection] = None,
) -> int:
    include_shared = agents is None
    files = managed_files(home, agents, include_shared=include_shared, selection=selection)
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


def _select_numbers(
    title: str, options: tuple[str, ...],
    *, multiple: bool = True, allow_skip: bool = True,
) -> tuple[str, ...]:
    mode = "可多选" if multiple else "单选"
    print(f"选择{title}（{mode}）：")
    for number, label in enumerate(options, 1):
        print(f"  {number}. {label}")
    all_number = len(options) + 1
    cancel_number = len(options) + (2 if multiple else 1)
    if multiple:
        print(f"  {all_number}. 全选")
    if allow_skip:
        print("  0. 跳过")
    print(f"  {cancel_number}. 取消安装")
    print("输入数字，以空格或逗号分隔。")
    while True:
        try:
            answer = input(f"{title}: ").strip()
        except (EOFError, KeyboardInterrupt) as error:
            raise ValueError("安装已取消，未写入配置。") from error
        if answer == str(cancel_number):
            raise ValueError("安装已取消，未写入配置。")
        if allow_skip and answer == "0":
            return ()
        if multiple and answer == str(all_number):
            return options
        choices = answer.replace(",", " ").split()
        valid = {str(number): option for number, option in enumerate(options, 1)}
        if choices and (multiple or len(choices) == 1) and all(choice in valid for choice in choices):
            return tuple(dict.fromkeys(valid[choice] for choice in choices))
        print("请输入有效数字；空输入、名称和混合特殊选项无效。")


def _select_install_agents() -> tuple[str, ...]:
    return _select_numbers("Agent", SUPPORTED_AGENTS)


def _select_install_configuration() -> tuple[InstallSelection, bool]:
    if not sys.stdin.isatty():
        raise ValueError("安装需要交互终端，请直接运行安装脚本并输入数字选择。")
    agents = _select_install_agents()
    skills = tuple(sorted({name for name, _, _ in _skill_files(CONFIG_ROOT / "skills")}))
    mcps = tuple(json.loads(MCP_CONFIG_SOURCE.read_text(encoding="utf-8")))
    selected_skills = _select_numbers("Skill", skills) if agents else ()
    selected_mcps = _select_numbers("MCP", mcps) if agents else ()
    labels = ("全局 Agent 规则", "Git 全局忽略", "Ruff 默认配置")
    selected_configs = _select_numbers("开发工具配置", labels)
    configs = tuple(
        name for name, label in zip(("rules", "git", "ruff"), labels)
        if label in selected_configs
    )
    policy = _select_numbers(
        "已有不同内容的处理方式", ("保留已有内容", "以仓库内容覆盖"),
        multiple=False, allow_skip=False,
    )
    selection = InstallSelection(agents, selected_skills, selected_mcps, configs)
    return selection, policy == ("以仓库内容覆盖",)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("install", "update", "check", "uninstall"):
        command = commands.add_parser(name)
        command.add_argument("--home", type=Path, default=Path.home(), help=argparse.SUPPRESS)
        if name != "install":
            command.add_argument("--force", action="store_true", help="覆盖或删除存在本地修改的受管文件")
            command.add_argument(
                "--agent", action="append", choices=SUPPORTED_AGENTS, dest="agents",
                help="只管理指定 Agent，可重复使用",
            )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    home = args.home.expanduser().resolve()
    if args.command == "install":
        try:
            selection, force = _select_install_configuration()
        except (ValueError, OSError) as error:
            print(error, file=sys.stderr)
            return 2
        print(f"Context7 请按所用 Agent 单独安装：{CONTEXT7_INSTALL_DOCS}")
        result = install(home, force, selection.agents, selection=selection)
        if result != 0:
            return result
        result = manage_mcp_servers(
            home, "install", selection.agents, force=force, servers=selection.mcps
        )
        if result == 0:
            _write_json(_selection_path(home), asdict(selection))
        return result

    agents = tuple(dict.fromkeys(args.agents)) if args.agents else None
    try:
        selection = _read_selection(home)
    except (ValueError, OSError, TypeError) as error:
        print(f"无法读取安装选择：{error}", file=sys.stderr)
        return 2
    if selection is not None and agents is not None:
        agents = tuple(agent for agent in agents if agent in selection.agents)
    mcp_agents = agents if agents is not None else (selection.agents if selection else None)
    servers = selection.mcps if selection else None
    if args.command == "update":
        print(f"Context7 请按所用 Agent 单独安装：{CONTEXT7_INSTALL_DOCS}")
        result = update(home, args.force, agents, selection=selection)
        mcp_result = manage_mcp_servers(home, "update", mcp_agents, force=args.force, servers=servers)
        return result or mcp_result
    if args.command == "uninstall":
        result = uninstall(home, args.force, agents, selection=selection)
        if result != 0:
            return result
        result = manage_mcp_servers(home, "uninstall", mcp_agents, force=args.force, servers=servers)
        if result == 0 and agents is None:
            _selection_path(home).unlink(missing_ok=True)
            _remove_empty_parents(_selection_path(home).parent, home)
        elif result == 0 and selection is not None:
            remaining = tuple(agent for agent in selection.agents if agent not in agents)
            remaining_selection = InstallSelection(
                remaining, selection.skills, selection.mcps, selection.configs
            )
            _write_json(_selection_path(home), asdict(remaining_selection))
        return result
    if args.force:
        raise SystemExit("check 不支持 --force")
    result = check(home, agents, selection=selection)
    mcp_result = manage_mcp_servers(home, "check", mcp_agents, servers=servers)
    return result or mcp_result


if __name__ == "__main__":
    sys.exit(main())
