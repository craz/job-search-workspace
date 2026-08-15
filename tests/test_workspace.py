"""Unit tests for manifest validation and safe workspace operations."""

from __future__ import annotations

import ast
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.workspace import bootstrap, load_repositories, run


class ManifestTests(unittest.TestCase):
    """Verify repository identity and locked versions remain consistent."""

    def test_manifest_and_lock_have_the_same_repositories(self) -> None:
        """Every declared repository must have exactly one full commit lock."""
        repositories = load_repositories()

        self.assertEqual(6, len(repositories))
        self.assertEqual(len(repositories), len({repo.name for repo in repositories}))
        self.assertTrue(all(len(repo.commit) == 40 for repo in repositories))

    def test_missing_lock_entry_is_rejected(self) -> None:
        """An incomplete lock must fail before any workspace operation starts."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "repos.yaml"
            lock = root / "repos.lock.json"
            manifest.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "repositories": [
                            {
                                "name": "example",
                                "path": "example",
                                "url": "local",
                                "branch": "main",
                                "visibility": "public",
                                "role": "test",
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            lock.write_text(
                json.dumps({"schema_version": 1, "repositories": {}}),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "missing lock entry"):
                load_repositories(manifest, lock)


class BootstrapTests(unittest.TestCase):
    """Protect existing product checkouts from bootstrap mutations."""

    def test_existing_locked_repositories_are_not_changed(self) -> None:
        """Bootstrap must preserve the revision of every existing checkout."""
        repositories = load_repositories()
        projects_dir = Path("/data/Projects")
        before = {
            repo.name: subprocess.check_output(
                ["git", "-C", str(projects_dir / repo.path), "rev-parse", "HEAD"],
                text=True,
            ).strip()
            for repo in repositories
        }

        checks = bootstrap(repositories, projects_dir)

        after = {
            repo.name: subprocess.check_output(
                ["git", "-C", str(projects_dir / repo.path), "rev-parse", "HEAD"],
                text=True,
            ).strip()
            for repo in repositories
        }
        self.assertEqual(before, after)
        self.assertFalse(any(check.level == "ERROR" for check in checks))


class ProcessTests(unittest.TestCase):
    """Verify safeguards used by network-aware child processes."""

    def test_process_timeout_is_enforced(self) -> None:
        """A stalled subprocess must terminate within its configured bound."""
        with self.assertRaises(subprocess.TimeoutExpired):
            run(["python3", "-c", "import time; time.sleep(1)"], timeout=0.01)


class DocumentationTests(unittest.TestCase):
    """Enforce structural documentation on the workspace automation module."""

    def test_workspace_module_classes_and_functions_have_docstrings(self) -> None:
        """Reject undocumented modules, classes and functions in workspace.py."""
        source = Path("scripts/workspace.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        undocumented = [
            getattr(node, "name", "<module>")
            for node in ast.walk(tree)
            if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
            and not ast.get_docstring(node)
        ]

        self.assertEqual([], undocumented)


if __name__ == "__main__":
    unittest.main()
