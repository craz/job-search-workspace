from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.workspace import bootstrap, load_repositories, run


class ManifestTests(unittest.TestCase):
    def test_manifest_and_lock_have_the_same_repositories(self) -> None:
        repositories = load_repositories()

        self.assertEqual(6, len(repositories))
        self.assertEqual(len(repositories), len({repo.name for repo in repositories}))
        self.assertTrue(all(len(repo.commit) == 40 for repo in repositories))

    def test_missing_lock_entry_is_rejected(self) -> None:
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
    def test_existing_locked_repositories_are_not_changed(self) -> None:
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
    def test_process_timeout_is_enforced(self) -> None:
        with self.assertRaises(subprocess.TimeoutExpired):
            run(["python3", "-c", "import time; time.sleep(1)"], timeout=0.01)


if __name__ == "__main__":
    unittest.main()
