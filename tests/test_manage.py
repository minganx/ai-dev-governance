from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.manage import check, install, managed_files, uninstall


class ManageTest(unittest.TestCase):
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
                "@~/.config/agents/AGENTS.md\n",
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
