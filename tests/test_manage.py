from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from tools.manage import (
    CLAUDE_ENTRY,
    SUPPORTED_AGENTS,
    _select_install_agents,
    main,
    PI_PACKAGES,
    _skill_files,
    _require_context7_key,
    check,
    install,
    manage_mcp_servers,
    manage_third_party_packages,
    managed_files,
    uninstall,
    update,
)


class ManageTest(unittest.TestCase):
    @patch("tools.manage.sys.stdin.isatty", return_value=True)
    @patch("builtins.input", side_effect=["", "invalid", "2, omp codex"])
    def test_install_menu_requires_valid_explicit_selection(self, _: Mock, tty: Mock) -> None:
        self.assertEqual(_select_install_agents(), ("codex", "omp"))

    @patch("tools.manage.sys.stdin.isatty", return_value=True)
    def test_install_menu_all_and_cancel(self, _: Mock) -> None:
        with patch("builtins.input", return_value="all"):
            self.assertEqual(_select_install_agents(), SUPPORTED_AGENTS)
        with patch("builtins.input", return_value="q"):
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

    @patch("tools.manage._select_install_agents")
    @patch("tools.manage.manage_mcp_servers", return_value=0)
    @patch("tools.manage.manage_third_party_packages", return_value=0)
    @patch("tools.manage.install", return_value=0)
    def test_explicit_install_agent_skips_menu(self, install_mock: Mock, packages: Mock, mcp: Mock, menu: Mock) -> None:
        with patch("sys.argv", ["manage.py", "install", "--agent", "omp"]):
            self.assertEqual(main(), 0)
        menu.assert_not_called()
        self.assertEqual(install_mock.call_args.args[2], ("omp",))
        self.assertEqual(packages.call_args.args[2], ("omp",))
        self.assertEqual(mcp.call_args.args[2], ("omp",))

    @patch.dict("os.environ", {"CONTEXT7_API_KEY": "test-key"}, clear=False)
    def test_retired_json_mcp_is_detected_and_removed(self) -> None:
        paths = {
            "claude": ".claude.json",
            "cursor": ".cursor/mcp.json",
            "pi": ".config/mcp/mcp.json",
            "omp": ".omp/agent/mcp.json",
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

    @patch.dict("os.environ", {"CONTEXT7_API_KEY": "test-key"}, clear=False)
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

    def test_omp_files_lifecycle_isolated_from_pi(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            self.assertEqual(install(home, force=False, agents=("omp",)), 0)
            rule = home / ".omp" / "agent" / "AGENTS.md"
            skill = home / ".omp" / "agent" / "skills" / "review-code" / "SKILL.md"
            self.assertTrue(rule.is_file())
            self.assertTrue(skill.is_file())
            self.assertFalse((home / ".pi").exists())
            self.assertFalse((home / ".agents").exists())
            self.assertEqual(check(home, agents=("omp",)), 0)
            rule.write_text("local", encoding="utf-8")
            skill.unlink()
            self.assertEqual(update(home, force=False, agents=("omp",)), 2)
            self.assertTrue(skill.is_file())
            self.assertEqual(rule.read_text(encoding="utf-8"), "local")
            self.assertEqual(uninstall(home, force=False, agents=("omp",)), 2)
            self.assertEqual(update(home, force=True, agents=("omp",)), 0)
            self.assertEqual(uninstall(home, force=False, agents=("omp",)), 0)
            self.assertFalse((home / ".omp").exists())
            self.assertTrue((home / ".config" / "agents" / "AGENTS.md").is_file())

    @patch.dict("os.environ", {"CONTEXT7_API_KEY": "test-context7-key"}, clear=False)
    def test_omp_mcp_lifecycle_preserves_other_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            config = home / ".omp" / "agent" / "mcp.json"
            config.parent.mkdir(parents=True)
            original = {"disabledServers": ["local"], "mcpServers": {"local": {"command": "local"}}}
            config.write_text(json.dumps(original), encoding="utf-8")
            self.assertEqual(manage_mcp_servers(home, "install", agents=("omp",)), 0)
            content = config.read_text(encoding="utf-8")
            servers = json.loads(content)["mcpServers"]
            self.assertEqual(set(servers), {"local", "context7", "deepwiki"})
            self.assertEqual(servers["deepwiki"]["type"], "http")
            self.assertEqual(servers["context7"]["type"], "stdio")
            self.assertNotIn("test-context7-key", content)
            self.assertFalse((home / ".config" / "mcp").exists())
            self.assertEqual(manage_mcp_servers(home, "check", agents=("omp",)), 0)
            self.assertEqual(manage_mcp_servers(home, "uninstall", agents=("omp",)), 0)
            self.assertEqual(json.loads(config.read_text(encoding="utf-8")), original)

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
    @patch("tools.manage.shutil.which", return_value="/usr/local/bin/pi")
    def test_pi_install_manages_required_packages(self, _: Mock, run: Mock) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            run.side_effect = [
                Mock(returncode=0, stdout="User packages:\n", stderr=""),
                *[Mock(returncode=0) for _ in PI_PACKAGES],
            ]

            self.assertEqual(
                manage_third_party_packages(home, "install", agents=("pi",)),
                0,
            )

            list_call, *install_calls = run.call_args_list
            self.assertEqual(list_call.args[0], ["/usr/local/bin/pi", "list"])
            self.assertEqual(
                [call.args[0] for call in install_calls],
                [
                    ["/usr/local/bin/pi", "install", package]
                    for package in PI_PACKAGES
                ],
            )
            self.assertEqual(
                install_calls[0].kwargs["env"]["PI_CODING_AGENT_DIR"],
                str(home / ".pi" / "agent"),
            )

    @patch("tools.manage.subprocess.run")
    @patch("tools.manage.shutil.which")
    def test_non_pi_agent_does_not_manage_pi_packages(
        self,
        which: Mock,
        run: Mock,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(
                manage_third_party_packages(
                    Path(directory),
                    "install",
                    agents=("claude", "omp"),
                ),
                0,
            )
            which.assert_not_called()
            run.assert_not_called()

    @patch.dict("os.environ", {"CONTEXT7_API_KEY": "test-context7-key"}, clear=False)
    def test_pi_mcp_sync_uses_shared_config_without_plaintext_key(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)

            self.assertEqual(
                manage_mcp_servers(home, "install", agents=("pi",)),
                0,
            )
            config = home / ".config" / "mcp" / "mcp.json"
            content = config.read_text(encoding="utf-8")
            self.assertEqual(set(json.loads(content)["mcpServers"]), {"context7", "deepwiki"})
            self.assertIn('"context7"', content)
            self.assertIn('"deepwiki"', content)
            self.assertNotIn("test-context7-key", content)
            self.assertEqual(
                (home / ".config" / "agents" / "mcp" / "context7-api-key")
                .read_text(encoding="utf-8")
                .strip(),
                "test-context7-key",
            )
            self.assertEqual(
                manage_mcp_servers(home, "check", agents=("pi",)),
                0,
            )

    @patch("tools.manage.subprocess.run")
    @patch("tools.manage.shutil.which", return_value="/usr/local/bin/codex")
    @patch.dict("os.environ", {"CONTEXT7_API_KEY": "test-context7-key"}, clear=False)
    def test_codex_mcp_sync_uses_official_cli(self, _: Mock, run: Mock) -> None:
        with tempfile.TemporaryDirectory() as directory:
            run.side_effect = [
                Mock(returncode=0, stdout="[]", stderr=""),
                Mock(returncode=0),
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
                ["context7", "deepwiki"],
            )

    @patch.dict("os.environ", {"CONTEXT7_API_KEY": "test-context7-key"}, clear=False)
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
            self.assertNotEqual(servers["context7"]["command"], "custom-context7")

    @patch.dict("os.environ", {}, clear=True)
    @patch("tools.manage.getpass.getpass", return_value="pasted-key")
    @patch("tools.manage.sys.stdin.isatty", return_value=True)
    def test_context7_key_prompts_once_and_saves_locally(
        self,
        _: Mock,
        getpass_mock: Mock,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)

            self.assertEqual(_require_context7_key(home), "pasted-key")
            self.assertEqual(_require_context7_key(home), "pasted-key")
            getpass_mock.assert_called_once()

    def test_install_and_check(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)

            self.assertEqual(install(home, force=False), 0)
            self.assertEqual(check(home), 0)
            self.assertTrue(all(item.target.is_file() for item in managed_files(home)))
            shared_agents = (home / ".config" / "agents" / "AGENTS.md").read_text(
                encoding="utf-8"
            )
            self.assertEqual(
                (home / ".codex" / "AGENTS.md").read_text(encoding="utf-8"),
                shared_agents,
            )
            self.assertEqual(
                (home / ".pi" / "agent" / "AGENTS.md").read_text(encoding="utf-8"),
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

            self.assertEqual(install(home, force=False, agents=("pi",)), 0)
            self.assertEqual(check(home, agents=("pi",)), 0)
            self.assertTrue((home / ".config" / "agents" / "AGENTS.md").is_file())
            self.assertTrue((home / ".pi" / "agent" / "AGENTS.md").is_file())
            self.assertTrue(
                (home / ".agents" / "skills" / "review-code" / "SKILL.md").is_file()
            )
            self.assertFalse((home / ".claude").exists())
            self.assertFalse((home / ".codex").exists())
            self.assertFalse((home / ".cursor").exists())

    def test_update_adds_missing_files_and_preserves_local_changes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)

            self.assertEqual(install(home, force=False, agents=("pi",)), 0)
            local_file = home / ".pi" / "agent" / "AGENTS.md"
            missing_file = (
                home / ".agents" / "skills" / "review-code" / "SKILL.md"
            )
            local_file.write_text("local change", encoding="utf-8")
            missing_file.unlink()

            self.assertEqual(update(home, force=False, agents=("pi",)), 2)
            self.assertEqual(local_file.read_text(encoding="utf-8"), "local change")
            self.assertTrue(missing_file.is_file())

            self.assertEqual(update(home, force=True, agents=("pi",)), 0)
            self.assertEqual(check(home, agents=("pi",)), 0)

    def test_uninstalls_selected_agent_without_removing_shared_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)

            self.assertEqual(install(home, force=False), 0)
            self.assertEqual(uninstall(home, force=False, agents=("pi",)), 0)
            self.assertFalse((home / ".pi").exists())
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
