from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.manage import check, install, managed_files


class ManageTest(unittest.TestCase):
    def test_install_and_check(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)

            self.assertEqual(install(home, force=False), 0)
            self.assertEqual(check(home), 0)
            self.assertTrue(all(item.target.is_file() for item in managed_files(home)))
            self.assertEqual(
                (home / ".codex" / "AGENTS.md").read_text(encoding="utf-8"),
                (home / ".config" / "agents" / "AGENTS.md").read_text(encoding="utf-8"),
            )
            self.assertEqual(
                (home / ".claude" / "CLAUDE.md").read_text(encoding="utf-8"),
                "@~/.config/agents/AGENTS.md\n",
            )

    def test_refuses_to_overwrite_drift_without_force(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            target = managed_files(home)[0].target
            target.parent.mkdir(parents=True)
            target.write_text("local change", encoding="utf-8")

            self.assertEqual(install(home, force=False), 2)
            self.assertEqual(target.read_text(encoding="utf-8"), "local change")
            self.assertEqual(install(home, force=True), 0)
            self.assertEqual(check(home), 0)


if __name__ == "__main__":
    unittest.main()
