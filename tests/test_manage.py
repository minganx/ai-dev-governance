from __future__ import annotations

import io
import json
import tempfile
import unittest
from pathlib import Path
from typing import Optional
from unittest.mock import Mock, patch

from tools.manage import (
    CLAUDE_ENTRY,
    SUPPORTED_AGENTS,
    build_parser,
    _select_install_agents,
    _select_numbers,
    main,
    _skill_files,
    check,
    install,
    manage_mcp_servers,
    managed_files,
    uninstall,
    update,
)


class ManageTest(unittest.TestCase):
    @patch("tools.manage.sys.stdin.isatty", return_value=True)
    @patch("builtins.input", side_effect=["", "codex", "0 1", "9", "2, 3 2"])
    def test_install_menu_requires_valid_explicit_selection(self, _: Mock, tty: Mock) -> None:
        self.assertEqual(_select_install_agents(), ("codex", "cursor"))

    @patch("tools.manage.sys.stdin.isatty", return_value=True)
    def test_install_menu_all_and_cancel(self, _: Mock) -> None:
        with patch("builtins.input", return_value="4"):
            self.assertEqual(_select_install_agents(), SUPPORTED_AGENTS)
        with patch("builtins.input", return_value="5"):
            with self.assertRaises(ValueError):
                _select_install_agents()
        with patch("builtins.input", side_effect=EOFError):
            with self.assertRaises(ValueError):
                _select_install_agents()

    @patch("tools.manage.sys.stdin.isatty", return_value=False)
    @patch("tools.manage.install")
    def test_noninteractive_install_without_agents_writes_nothing(self, install_mock: Mock, _: Mock) -> None:
        with patch("sys.argv", ["manage.py", "install"]):
            self.assertEqual(main(), 2)
        install_mock.assert_not_called()

    def test_install_rejects_configuration_parameters(self) -> None:
        for arguments in (["--agent", "cursor"], ["--force"], ["--skill", "review-code"], ["--mcp", "deepwiki"]):
            with self.subTest(arguments=arguments), patch("sys.stderr", new_callable=io.StringIO):
                with self.assertRaises(SystemExit) as error:
                    build_parser().parse_args(["install", *arguments])
                self.assertEqual(error.exception.code, 2)

    def test_number_menu_skip_single_choice_and_interrupt(self) -> None:
        with patch("builtins.input", return_value="0"):
            self.assertEqual(_select_install_agents(), ())
        with patch("builtins.input", side_effect=["0", "1 2", "2"]):
            self.assertEqual(_select_numbers("策略", ("保留", "覆盖"), multiple=False, allow_skip=False), ("覆盖",))
        with patch("builtins.input", side_effect=KeyboardInterrupt):
            with self.assertRaises(ValueError):
                _select_install_agents()

    def _run_main(self, home: Path, command: str, answers: Optional[list[str]] = None, *arguments: str) -> int:
        with patch("sys.argv", ["manage.py", command, "--home", str(home), *arguments]):
            with patch("tools.manage.sys.stdin.isatty", return_value=True):
                with patch("builtins.input", side_effect=answers or []):
                    return main()

    def test_install_cancel_at_each_stage_writes_nothing(self) -> None:
        for answers in (["5"], ["3", "7"], ["3", "0", "3"], ["3", "0", "0", "5"], ["3", "0", "0", "0", "3"]):
            with self.subTest(answers=answers), tempfile.TemporaryDirectory() as directory:
                home = Path(directory)
                self.assertEqual(self._run_main(home, "install", list(answers)), 2)
                self.assertEqual(list(home.iterdir()), [])

    def test_install_selection_controls_update_check_and_uninstall(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            # Cursor; review-code only; no MCP; Git only; preserve conflicts.
            self.assertEqual(self._run_main(home, "install", ["3", "4", "0", "2", "1"]), 0)
            skill = home / ".cursor" / "skills" / "review-code" / "SKILL.md"
            state = home / ".config" / "agents" / "install-selection.json"
            self.assertTrue(skill.is_file())
            self.assertEqual(json.loads(state.read_text()), {
                "agents": ["cursor"], "skills": ["review-code"], "mcps": [], "configs": ["git"],
            })
            self.assertFalse((home / ".cursor" / "mcp.json").exists())
            self.assertFalse((home / ".config" / "ruff").exists())
            self.assertFalse((home / ".config" / "agents" / "AGENTS.md").exists())
            self.assertFalse((home / ".claude").exists())
            self.assertFalse((home / ".codex").exists())
            skill.unlink()
            self.assertEqual(self._run_main(home, "check"), 1)
            self.assertEqual(self._run_main(home, "update"), 0)
            self.assertTrue(skill.is_file())
            self.assertEqual(self._run_main(home, "check"), 0)
            self.assertEqual(len(list((home / ".cursor" / "skills").iterdir())), 1)
            self.assertFalse((home / ".cursor" / "mcp.json").exists())
            self.assertFalse((home / ".config" / "ruff").exists())
            self.assertEqual(self._run_main(home, "uninstall"), 0)
            self.assertEqual(list(home.iterdir()), [])

    @patch("tools.manage.subprocess.run")
    def test_all_agents_with_skipped_mcp_need_no_agent_cli(self, run: Mock) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            self.assertEqual(self._run_main(home, "install", ["4", "6", "0", "4", "1"]), 0)
            for agent in (".claude", ".codex", ".cursor"):
                self.assertTrue((home / agent / "skills" / "review-code" / "SKILL.md").is_file())
            for action in ("update", "check", "uninstall"):
                self.assertEqual(self._run_main(home, action), 0)
            run.assert_not_called()
            self.assertEqual(list(home.iterdir()), [])

    def test_install_mcp_only_and_preserve_context7(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            config = home / ".cursor" / "mcp.json"
            config.parent.mkdir()
            context7 = {"url": "https://custom.example", "headers": {"key": "local"}}
            config.write_text(json.dumps({"mcpServers": {"context7": context7}}))
            self.assertEqual(self._run_main(home, "install", ["3", "0", "1", "0", "1"]), 0)
            self.assertEqual(set(json.loads(config.read_text())["mcpServers"]), {"context7", "deepwiki"})
            self.assertFalse((home / ".cursor" / "skills").exists())
            self.assertEqual(self._run_main(home, "check"), 0)
            self.assertEqual(self._run_main(home, "uninstall"), 0)
            self.assertEqual(json.loads(config.read_text()), {"mcpServers": {"context7": context7}})

    def test_install_without_agents_only_selected_developer_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            self.assertEqual(self._run_main(home, "install", ["0", "2", "1"]), 0)
            self.assertTrue((home / ".gitignore_global").is_file())
            for agent in (".claude", ".codex", ".cursor"):
                self.assertFalse((home / agent).exists())
            self.assertEqual(self._run_main(home, "update"), 0)
            self.assertEqual(self._run_main(home, "check"), 0)
            self.assertEqual(self._run_main(home, "uninstall"), 0)
            self.assertEqual(list(home.iterdir()), [])

    def test_install_conflict_policy_selected_by_number(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            target = home / ".gitignore_global"
            target.write_text("local")
            self.assertEqual(self._run_main(home, "install", ["0", "2", "1"]), 2)
            self.assertEqual(target.read_text(), "local")
            self.assertFalse((home / ".config" / "agents" / "install-selection.json").exists())
            self.assertEqual(self._run_main(home, "install", ["0", "2", "2"]), 0)
            self.assertNotEqual(target.read_text(), "local")

    def test_partial_uninstall_updates_selection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            self.assertEqual(self._run_main(home, "install", ["1 3", "4", "0", "1", "1"]), 0)
            self.assertEqual(self._run_main(home, "uninstall", None, "--agent", "claude"), 0)
            state = home / ".config" / "agents" / "install-selection.json"
            self.assertEqual(json.loads(state.read_text())["agents"], ["cursor"])
            self.assertEqual(self._run_main(home, "update"), 0)
            self.assertFalse((home / ".claude").exists())
            self.assertTrue((home / ".cursor" / "skills" / "review-code" / "SKILL.md").is_file())
            self.assertEqual(self._run_main(home, "check"), 0)

    def test_invalid_selection_record_stops_before_writing(self) -> None:
        for document in ([], {"agents": "cursor", "skills": [], "mcps": [], "configs": []},
                         {"agents": ["pi"], "skills": [], "mcps": [], "configs": []},
                         {"agents": [], "skills": [], "mcps": [], "configs": ["unknown"]}):
            with self.subTest(document=document), tempfile.TemporaryDirectory() as directory:
                home = Path(directory)
                state = home / ".config" / "agents" / "install-selection.json"
                state.parent.mkdir(parents=True)
                state.write_text(json.dumps(document))
                self.assertEqual(self._run_main(home, "update"), 2)
                self.assertEqual(list(home.iterdir()), [home / ".config"])
                self.assertEqual(json.loads(state.read_text()), document)

    def test_retired_json_mcp_is_detected_and_removed(self) -> None:
        paths = {
            "claude": ".claude.json",
            "cursor": ".cursor/mcp.json",
        }
        for agent, relative in paths.items():
            for action in ("install", "update", "uninstall"):
                with self.subTest(agent=agent, action=action), tempfile.TemporaryDirectory() as directory:
                    home = Path(directory)
                    self.assertEqual(manage_mcp_servers(home, "install", (agent,)), 0)
                    config = home / relative
                    document = json.loads(config.read_text())
                    document["mcpServers"].update({
                        "codegraph": {"command": "codegraph", "args": ["serve", "--mcp"]},
                        "local": {"command": "local"},
                    })
                    config.write_text(json.dumps(document))
                    self.assertEqual(manage_mcp_servers(home, "check", (agent,)), 1)
                    self.assertEqual(manage_mcp_servers(home, action, (agent,)), 0)
                    servers = json.loads(config.read_text())["mcpServers"]
                    self.assertNotIn("codegraph", servers)
                    self.assertEqual(servers["local"], {"command": "local"})
                    self.assertEqual(manage_mcp_servers(home, action, (agent,)), 0)

    @patch("tools.manage._read_codex_mcp_servers")
    @patch("tools.manage._run_codex_mcp_command", return_value=0)
    def test_codex_retirement_uses_remove_and_propagates_failure(self, command: Mock, read: Mock) -> None:
        read.return_value = ("codex", {"codegraph": {"command": "codegraph"}})
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            self.assertEqual(manage_mcp_servers(home, "update", ("codex",)), 0)
            self.assertEqual(command.call_args_list[0].args, (home, "codex", "remove", "codegraph"))
            command.reset_mock()
            command.return_value = 1
            self.assertEqual(manage_mcp_servers(home, "update", ("codex",)), 1)
            command.assert_called_once_with(home, "codex", "remove", "codegraph")

    def test_parser_rejects_removed_agents(self) -> None:
        self.assertEqual(SUPPORTED_AGENTS, ("claude", "codex", "cursor"))
        for agent in ("pi", "omp", "opencode"):
            with self.subTest(agent=agent), patch("sys.stderr", new_callable=io.StringIO):
                with self.assertRaises(SystemExit) as error:
                    build_parser().parse_args(["update", "--agent", agent])
                self.assertEqual(error.exception.code, 2)

    def test_context7_notice_once_per_install_or_update(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            for action in ("install", "update"):
                with patch("sys.stdout", new_callable=io.StringIO) as output:
                    answers = ["3", "0", "0", "0", "1"] if action == "install" else None
                    self.assertEqual(self._run_main(home, action, answers), 0)
                self.assertEqual(output.getvalue().count("Context7"), 1)
                self.assertIn("https://context7.com/docs/resources/all-clients", output.getvalue())

    def test_skill_files_include_supporting_resources(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            skills_root = Path(directory)
            skill_root = skills_root / "notes"
            (skill_root / "scripts").mkdir(parents=True)
            (skill_root / "SKILL.md").write_text("skill", encoding="utf-8")
            (skill_root / "scripts" / "export.py").write_text("script", encoding="utf-8")
            ignored = skills_root / "not-a-skill"
            ignored.mkdir()
            (ignored / "README.md").write_text("ignored", encoding="utf-8")

            files = _skill_files(skills_root)

            self.assertEqual(
                [(name, relative.as_posix()) for name, _, relative in files],
                [("notes", "SKILL.md"), ("notes", "scripts/export.py")],
            )

    @patch("tools.manage.subprocess.run")
    @patch("tools.manage.shutil.which", return_value="/usr/local/bin/codex")
    def test_codex_mcp_sync_uses_official_cli(self, _: Mock, run: Mock) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run.side_effect = [
                Mock(returncode=0, stdout="[]", stderr=""),
                Mock(returncode=0),
            ]

            self.assertEqual(
                manage_mcp_servers(
                    Path(directory),
                    "install",
                    agents=("codex",),
                ),
                0,
            )
            commands = [call.args[0] for call in run.call_args_list]
            self.assertEqual(
                commands[0],
                ["/usr/local/bin/codex", "mcp", "list", "--json"],
            )
            self.assertEqual(
                [command[3] for command in commands[1:]],
                ["deepwiki"],
            )

    def test_mcp_sync_preserves_unmanaged_cursor_servers_and_drift(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            config = home / ".cursor" / "mcp.json"
            config.parent.mkdir(parents=True)
            config.write_text(
                json.dumps(
                    {
                        "mcpServers": {
                            "local": {"command": "local-mcp"},
                            "context7": {"command": "custom-context7"},
                            "deepwiki": {"url": "https://custom.example/mcp"},
                        }
                    }
                ),
                encoding="utf-8",
            )

            self.assertEqual(
                manage_mcp_servers(home, "update", agents=("cursor",)),
                2,
            )
            servers = json.loads(config.read_text(encoding="utf-8"))["mcpServers"]
            self.assertEqual(servers["local"]["command"], "local-mcp")
            self.assertEqual(servers["context7"]["command"], "custom-context7")
            self.assertIn("deepwiki", servers)

            self.assertEqual(
                manage_mcp_servers(home, "uninstall", agents=("cursor",)),
                2,
            )
            servers = json.loads(config.read_text(encoding="utf-8"))["mcpServers"]
            self.assertIn("deepwiki", servers)

            self.assertEqual(
                manage_mcp_servers(
                    home,
                    "update",
                    agents=("cursor",),
                    force=True,
                ),
                0,
            )
            servers = json.loads(config.read_text(encoding="utf-8"))["mcpServers"]
            self.assertEqual(servers["local"]["command"], "local-mcp")
            self.assertEqual(servers["context7"]["command"], "custom-context7")
            self.assertEqual(manage_mcp_servers(home, "check", ("cursor",)), 0)
            self.assertEqual(manage_mcp_servers(home, "uninstall", ("cursor",), force=True), 0)
            servers = json.loads(config.read_text())["mcpServers"]
            self.assertEqual(servers["context7"], {"command": "custom-context7"})
            self.assertNotIn("deepwiki", servers)
            self.assertFalse((home / ".config" / "agents" / "mcp").exists())

    def test_context7_legacy_files_are_unmanaged(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            legacy = home / ".config" / "agents" / "mcp"
            legacy.mkdir(parents=True)
            wrapper = legacy / "context7_mcp.py"
            secret = legacy / "context7-api-key"
            wrapper.write_text("local wrapper", encoding="utf-8")
            secret.write_text("local key", encoding="utf-8")
            for action in ("install", "update", "check", "uninstall"):
                self.assertEqual(manage_mcp_servers(home, action, ("cursor",), force=True), 0)
                self.assertEqual(wrapper.read_text(), "local wrapper")
                self.assertEqual(secret.read_text(), "local key")

    def test_install_and_check(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)

            self.assertEqual(install(home, force=False), 0)
            self.assertEqual(check(home), 0)
            self.assertTrue(all(item.target.is_file() for item in managed_files(home)))
            for retired in (".pi", ".omp", ".agents"):
                self.assertFalse((home / retired).exists())
            shared_agents = (home / ".config" / "agents" / "AGENTS.md").read_text(
                encoding="utf-8"
            )
            self.assertEqual(
                (home / ".codex" / "AGENTS.md").read_text(encoding="utf-8"),
                shared_agents,
            )
            self.assertEqual(
                (home / ".claude" / "CLAUDE.md").read_text(encoding="utf-8"),
                CLAUDE_ENTRY.read_text(encoding="utf-8"),
            )
            self.assertTrue((home / ".gitignore_global").is_file())
            self.assertTrue(any(item.source.name == "ruff.toml" for item in managed_files(home)))

    def test_installs_only_selected_agent_and_shared_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)

            self.assertEqual(install(home, force=False, agents=("claude",)), 0)
            self.assertEqual(check(home, agents=("claude",)), 0)
            self.assertTrue((home / ".config" / "agents" / "AGENTS.md").is_file())
            self.assertTrue((home / ".claude" / "CLAUDE.md").is_file())
            self.assertTrue(
                (home / ".claude" / "skills" / "review-code" / "SKILL.md").is_file()
            )
            self.assertFalse((home / ".codex").exists())
            self.assertFalse((home / ".cursor").exists())

    def test_update_adds_missing_files_and_preserves_local_changes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)

            self.assertEqual(install(home, force=False, agents=("claude",)), 0)
            local_file = home / ".claude" / "CLAUDE.md"
            missing_file = (
                home / ".claude" / "skills" / "review-code" / "SKILL.md"
            )
            local_file.write_text("local change", encoding="utf-8")
            missing_file.unlink()

            self.assertEqual(update(home, force=False, agents=("claude",)), 2)
            self.assertEqual(local_file.read_text(encoding="utf-8"), "local change")
            self.assertTrue(missing_file.is_file())

            self.assertEqual(update(home, force=True, agents=("claude",)), 0)
            self.assertEqual(check(home, agents=("claude",)), 0)

    def test_uninstalls_selected_agent_without_removing_shared_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)

            self.assertEqual(install(home, force=False), 0)
            self.assertEqual(uninstall(home, force=False, agents=("claude",)), 0)
            self.assertFalse((home / ".claude").exists())
            self.assertFalse((home / ".agents").exists())
            self.assertTrue((home / ".config" / "agents" / "AGENTS.md").is_file())
            self.assertTrue((home / ".codex" / "AGENTS.md").is_file())

    def test_uninstalls_all_managed_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)

            self.assertEqual(install(home, force=False), 0)
            files = managed_files(home)
            self.assertEqual(uninstall(home, force=False), 0)
            self.assertFalse(any(item.target.exists() for item in files))

    def test_refuses_to_overwrite_or_remove_drift_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            target = managed_files(home)[0].target
            target.parent.mkdir(parents=True)
            target.write_text("local change", encoding="utf-8")

            self.assertEqual(install(home, force=False), 2)
            self.assertEqual(target.read_text(encoding="utf-8"), "local change")
            self.assertEqual(install(home, force=True), 0)
            self.assertEqual(check(home), 0)

            target.write_text("another local change", encoding="utf-8")
            self.assertEqual(uninstall(home, force=False), 2)
            self.assertEqual(
                target.read_text(encoding="utf-8"), "another local change"
            )
            self.assertEqual(uninstall(home, force=True), 0)
            self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
