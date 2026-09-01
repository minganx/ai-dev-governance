from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from tools.manage import (
    CLAUDE_ENTRY,
    PI_CURSOR_PACKAGE,
    _skill_files,
    check,
    install,
    manage_third_party_packages,
    managed_files,
    uninstall,
    update,
)


class ManageTest(unittest.TestCase):
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
    def test_pi_install_manages_cursor_package(self, _: Mock, run: Mock) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            run.side_effect = [
                Mock(returncode=0, stdout="User packages:\n", stderr=""),
                Mock(returncode=0),
            ]

            self.assertEqual(
                manage_third_party_packages(home, "install", agents=("pi",)),
                0,
            )

            list_call, install_call = run.call_args_list
            self.assertEqual(list_call.args[0], ["/usr/local/bin/pi", "list"])
            self.assertEqual(
                install_call.args[0],
                ["/usr/local/bin/pi", "install", PI_CURSOR_PACKAGE],
            )
            self.assertEqual(
                install_call.kwargs["env"]["PI_CODING_AGENT_DIR"],
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
                    agents=("claude",),
                ),
                0,
            )
            which.assert_not_called()
            run.assert_not_called()

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
