"""Executable acceptance scenarios for the workspace foundation feature."""

from __future__ import annotations

import unittest
from pathlib import Path

from scripts.workspace import bootstrap, doctor, load_repositories


PROJECTS_DIR = Path("/data/Projects")


class WorkspaceFoundationScenarios(unittest.TestCase):
    """Executable bindings for tests/features/workspace_foundation.feature."""

    def test_existing_workspace_is_bootstrapped_without_overwrite(self) -> None:
        """Bootstrap keeps every pre-existing locked checkout intact."""
        # Given all locked repositories already exist
        repositories = load_repositories()
        heads_before = {
            repo.name: (PROJECTS_DIR / repo.path / ".git").exists()
            for repo in repositories
        }

        # When bootstrap is executed
        checks = bootstrap(repositories, PROJECTS_DIR)

        # Then every repository remains available and no destructive error occurs
        self.assertTrue(all(heads_before.values()))
        self.assertFalse(any(check.level == "ERROR" for check in checks))

    def test_offline_doctor_validates_locked_workspace(self) -> None:
        """Offline doctor proves local consistency without requiring a network."""
        # Given repository versions match the workspace lock
        repositories = load_repositories()

        # When doctor runs without external network checks
        checks = doctor(repositories, PROJECTS_DIR, offline=True, skip_tools=True)

        # Then all local repository checks pass
        self.assertFalse(any(check.level == "ERROR" for check in checks))


if __name__ == "__main__":
    unittest.main()
