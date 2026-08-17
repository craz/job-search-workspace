"""Executable acceptance scenarios for the workspace foundation feature."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

from scripts.workspace import bootstrap, doctor, load_repositories
from tests.test_workspace import BootstrapTests


WORKSPACE_ROOT = Path(__file__).resolve().parent.parent


class WorkspaceFoundationScenarios(unittest.TestCase):
    """Executable bindings for tests/features/workspace_foundation.feature."""

    def test_missing_service_submodule_is_initialized(self) -> None:
        """Bootstrap realizes a recorded gitlink in an isolated fresh clone."""
        scenario = BootstrapTests("test_missing_submodule_is_initialized_at_recorded_gitlink")
        scenario.test_missing_submodule_is_initialized_at_recorded_gitlink()

    def test_existing_workspace_is_bootstrapped_without_overwrite(self) -> None:
        """Bootstrap keeps every initialized submodule checkout intact."""
        # Given all recorded submodules are already initialized
        repositories = load_repositories()
        heads_before = {
            repo.name: subprocess.check_output(
                ["git", "-C", str(WORKSPACE_ROOT / repo.path), "rev-parse", "HEAD"],
                text=True,
            ).strip()
            for repo in repositories
        }

        # When bootstrap is executed
        checks = bootstrap(repositories, WORKSPACE_ROOT)

        # Then every repository remains available and no destructive error occurs
        heads_after = {
            repo.name: subprocess.check_output(
                ["git", "-C", str(WORKSPACE_ROOT / repo.path), "rev-parse", "HEAD"],
                text=True,
            ).strip()
            for repo in repositories
        }
        self.assertEqual(heads_before, heads_after)
        self.assertFalse(any(check.level == "ERROR" for check in checks))

    def test_offline_doctor_validates_locked_workspace(self) -> None:
        """Offline doctor proves gitlink consistency without network access."""
        # Given submodule revisions match the workspace gitlinks
        repositories = load_repositories()

        # When doctor runs without external network checks
        checks = doctor(repositories, WORKSPACE_ROOT, offline=True, skip_tools=True)

        # Then all local repository checks pass
        self.assertFalse(any(check.level == "ERROR" for check in checks))


if __name__ == "__main__":
    unittest.main()
