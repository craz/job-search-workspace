"""Unit tests for submodule declarations and safe workspace operations."""

from __future__ import annotations

import ast
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.workspace import bootstrap, load_repositories, run

ROOT = Path(__file__).resolve().parent.parent


class SubmoduleDeclarationTests(unittest.TestCase):
    """Verify repository identity comes from bounded Git submodules."""

    def test_all_product_submodules_are_declared_below_services(self) -> None:
        """Every product must have one explicit branch and canonical remote."""
        repositories = load_repositories()

        self.assertEqual(6, len(repositories))
        self.assertEqual(len(repositories), len({repo.name for repo in repositories}))
        self.assertTrue(all(repo.path.startswith("services/") for repo in repositories))
        self.assertTrue(all(repo.branch == "main" for repo in repositories))
        self.assertTrue(all(repo.url.startswith("git@github.com:craz/") for repo in repositories))

    def test_parent_traversal_is_rejected(self) -> None:
        """A submodule declaration cannot escape the workspace service tree."""
        with tempfile.TemporaryDirectory() as directory:
            gitmodules = Path(directory) / ".gitmodules"
            gitmodules.write_text(
                '[submodule "escape"]\n'
                "\tpath = services/../../escape\n"
                "\turl = git@example.invalid:escape.git\n"
                "\tbranch = main\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "invalid submodule declaration"):
                load_repositories(gitmodules)


class BootstrapTests(unittest.TestCase):
    """Protect initialized product submodules from bootstrap mutations."""

    def test_missing_submodule_is_initialized_at_recorded_gitlink(self) -> None:
        """A fresh superproject clone receives the exact recorded service commit."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            superproject = root / "superproject"
            checkout = root / "checkout"
            source.mkdir()
            superproject.mkdir()
            subprocess.run(["git", "init", "-q", "-b", "main"], cwd=source, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=source, check=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.invalid"], cwd=source, check=True
            )
            (source / "README.md").write_text("synthetic service\n")
            subprocess.run(["git", "add", "README.md"], cwd=source, check=True)
            subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=source, check=True)
            expected = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source, text=True).strip()

            subprocess.run(["git", "init", "-q", "-b", "main"], cwd=superproject, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=superproject, check=True)
            subprocess.run(
                ["git", "config", "user.email", "test@example.invalid"],
                cwd=superproject,
                check=True,
            )
            subprocess.run(
                [
                    "git",
                    "-c",
                    "protocol.file.allow=always",
                    "submodule",
                    "add",
                    "--name",
                    "example",
                    str(source),
                    "services/example",
                ],
                cwd=superproject,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            with (superproject / ".gitmodules").open("a") as stream:
                stream.write("\tbranch = main\n")
            subprocess.run(["git", "add", "."], cwd=superproject, check=True)
            subprocess.run(["git", "commit", "-q", "-m", "workspace"], cwd=superproject, check=True)
            subprocess.run(["git", "clone", "-q", str(superproject), str(checkout)], check=True)
            repositories = load_repositories(checkout / ".gitmodules")
            with patch.dict(os.environ, {"GIT_ALLOW_PROTOCOL": "file"}):
                checks = bootstrap(repositories, checkout)

            actual = subprocess.check_output(
                ["git", "-C", str(checkout / "services/example"), "rev-parse", "HEAD"],
                text=True,
            ).strip()
            self.assertEqual(expected, actual)
            self.assertFalse(any(check.level == "ERROR" for check in checks))

    def test_existing_locked_repositories_are_not_changed(self) -> None:
        """Bootstrap must preserve every initialized submodule revision."""
        repositories = load_repositories()
        before = {
            repo.name: subprocess.check_output(
                ["git", "-C", str(ROOT / repo.path), "rev-parse", "HEAD"],
                text=True,
            ).strip()
            for repo in repositories
        }

        checks = bootstrap(repositories, ROOT)

        after = {
            repo.name: subprocess.check_output(
                ["git", "-C", str(ROOT / repo.path), "rev-parse", "HEAD"],
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
