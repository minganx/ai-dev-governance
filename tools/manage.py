#!/usr/bin/env python3
"""跨平台管理 AI 开发规则、Skill、MCP 配置和受管 Pi Package。"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CONFIG_ROOT = REPOSITORY_ROOT / "config" / "agents"
CLAUDE_ENTRY = REPOSITORY_ROOT / "config" / "tool-entries" / "claude" / "CLAUDE.md"
GIT_IGNORE_SOURCE = REPOSITORY_ROOT / "config" / "git" / "gitignore_global"
RUFF_CONFIG_SOURCE = REPOSITORY_ROOT / "config" / "ruff" / "ruff.toml"
MCP_CONFIG_SOURCE = REPOSITORY_ROOT / "config" / "mcp" / "servers.json"
CONTEXT7_WRAPPER_SOURCE = REPOSITORY_ROOT / "config" / "mcp" / "context7_mcp.py"
SUPPORTED_AGENTS = ("claude", "codex", "cursor", "pi")
MCP_AGENTS = ("claude", "codex", "cursor", "pi")
PI_PACKAGES = (
    "npm:@rahularya01/pi-cursor",
    "npm:pi-mcp-adapter",
)
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


def _mcp_paths(home: Path) -> tuple[Path, Path]:
    root = home / ".config" / "agents" / "mcp"
    return root / "context7_mcp.py", root / "context7-api-key"


def _resolved_mcp_servers(home: Path, agent: str) -> dict[str, dict[str, Any]]:
    definitions = json.loads(MCP_CONFIG_SOURCE.read_text(encoding="utf-8"))
    wrapper, secret = _mcp_paths(home)
    python = sys.executable if os.name == "nt" else shutil.which("python3") or sys.executable
    replacements = {
        "@python": python,
        "@context7-wrapper": str(wrapper),
        "@context7-api-key": str(secret),
    }
    resolved: dict[str, dict[str, Any]] = {}
    for name, definition in definitions.items():
        if agent not in definition["agents"]:
            continue
        if definition["transport"] == "http":
            resolved[name] = {"transport": "http", "url": definition["url"]}
            continue
        args = definition.get("agentArgs", {}).get(agent, definition["args"])
        resolved[name] = {
            "transport": "stdio",
            "command": replacements.get(definition["command"], definition["command"]),
            "args": [replacements.get(value, value) for value in args],
        }
    return resolved


def _json_mcp_path(home: Path, agent: str) -> Path:
    if agent == "claude":
        return home / ".claude.json"
    if agent == "cursor":
        return home / ".cursor" / "mcp.json"
    return home / ".config" / "mcp" / "mcp.json"


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


def _existing_context7_key(home: Path) -> Optional[str]:
    environment_key = os.environ.get("CONTEXT7_API_KEY", "").strip()
    if environment_key:
        return environment_key

    _, secret = _mcp_paths(home)
    if not secret.exists():
        return None
    saved = secret.read_text(encoding="utf-8").strip()
    return saved or None


def _save_context7_key(home: Path, api_key: str) -> None:
    _, secret = _mcp_paths(home)
    secret.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=secret.parent,
        delete=False,
    ) as handle:
        temporary = Path(handle.name)
        handle.write(api_key + "\n")
    os.chmod(temporary, 0o600)
    os.replace(temporary, secret)


def _require_context7_key(home: Path) -> Optional[str]:
    api_key = _existing_context7_key(home)
    if api_key:
        _save_context7_key(home, api_key)
        return api_key
    if not sys.stdin.isatty():
        print(
            "缺少 Context7 API Key。请在交互终端重新执行，或临时设置 CONTEXT7_API_KEY。",
            file=sys.stderr,
        )
        return None
    print("请先将 Context7 API Key 保存到密码管理器，然后在下方粘贴；输入不会回显。")
    api_key = getpass.getpass("Context7 API Key: ").strip()
    if not api_key:
        print("Context7 API Key 不能为空。", file=sys.stderr)
        return None
    _save_context7_key(home, api_key)
    return api_key


def manage_mcp_servers(
    home: Path,
    command: str,
    agents: Optional[tuple[str, ...]] = None,
    *,
    force: bool = False,
) -> int:
    selected = tuple(agent for agent in (agents or MCP_AGENTS) if agent in MCP_AGENTS)
    if not selected:
        return 0

    wrapper, secret = _mcp_paths(home)
    if command == "check":
        drifted: list[str] = []
        if not _same_content(CONTEXT7_WRAPPER_SOURCE, wrapper):
            drifted.append(str(wrapper))
        if not secret.is_file() or not secret.read_text(encoding="utf-8").strip():
            drifted.append(str(secret))
        for agent in selected:
            desired = _resolved_mcp_servers(home, agent)
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
            desired = _resolved_mcp_servers(home, agent)
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

    if command in ("install", "update"):
        if wrapper.exists() and not _same_content(CONTEXT7_WRAPPER_SOURCE, wrapper) and not force:
            print(f"MCP 启动器存在本地差异，已保留：{wrapper}", file=sys.stderr)
            return 2
        if not _same_content(CONTEXT7_WRAPPER_SOURCE, wrapper):
            _atomic_copy(CONTEXT7_WRAPPER_SOURCE, wrapper)
        if _require_context7_key(home) is None:
            return 1

    conflicts: list[str] = []
    for agent in selected:
        desired = _resolved_mcp_servers(home, agent)
        try:
            if agent == "codex":
                codex, current = _read_codex_mcp_servers(home)
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
                        if agent != "pi":
                            raw[name]["type"] = "http"
                    else:
                        raw[name] = {
                            "command": expected["command"],
                            "args": expected["args"],
                        }
                        if agent != "pi":
                            raw[name]["type"] = "stdio"
                    changed = True
            if changed:
                _write_json(_json_mcp_path(home, agent), document)
        except (json.JSONDecodeError, OSError, RuntimeError) as error:
            print(error, file=sys.stderr)
            return 1

    if command == "uninstall" and set(MCP_AGENTS).issubset(selected):
        if wrapper.is_file():
            wrapper.unlink()
        _remove_empty_parents(wrapper.parent, home)

    if conflicts:
        action = "删除" if command == "uninstall" else "覆盖"
        print(f"以下 MCP 配置存在本地差异，未{action}：", file=sys.stderr)
        for item in conflicts:
            print(f"- {item}", file=sys.stderr)
        return 2
    return 0


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

    missing = [package for package in PI_PACKAGES if package not in listed.stdout]
    if command == "check":
        if not missing:
            return 0
        for package in missing:
            print(f"缺少 Pi Package：{package}", file=sys.stderr)
        return 1

    for package in PI_PACKAGES:
        installed = package not in missing
        if command == "install" and installed:
            continue
        if command == "uninstall":
            if not installed:
                continue
            package_command = "remove"
        elif command == "update" and not installed:
            package_command = "install"
        else:
            package_command = command
        result = subprocess.run(
            [pi, package_command, package],
            env=environment,
            check=False,
        )
        if result.returncode != 0:
            return result.returncode
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
        package_result = manage_third_party_packages(home, "install", agents)
        if package_result != 0:
            return package_result
        return manage_mcp_servers(home, "install", agents, force=args.force)
    if args.command == "update":
        result = update(home, args.force, agents)
        package_result = manage_third_party_packages(home, "update", agents)
        mcp_result = manage_mcp_servers(home, "update", agents, force=args.force)
        return result or package_result or mcp_result
    if args.command == "uninstall":
        result = uninstall(home, args.force, agents)
        if result != 0:
            return result
        mcp_result = manage_mcp_servers(home, "uninstall", agents, force=args.force)
        if mcp_result != 0:
            return mcp_result
        return manage_third_party_packages(home, "uninstall", agents)
    if args.force:
        raise SystemExit("check 不支持 --force")
    result = check(home, agents)
    package_result = manage_third_party_packages(home, "check", agents)
    mcp_result = manage_mcp_servers(home, "check", agents)
    return result or package_result or mcp_result


if __name__ == "__main__":
    sys.exit(main())
