"""Workspace coverage for autostart helper rendering and Makefile wiring."""

from __future__ import annotations

import unittest
from pathlib import Path

from scripts import autostart


class AutostartWorkspaceTests(unittest.TestCase):
    def test_makefile_exposes_autostart_targets(self) -> None:
        makefile = (Path(__file__).resolve().parents[1] / "Makefile").read_text(encoding="utf-8")
        self.assertIn("install-autostart", makefile)
        self.assertIn("uninstall-autostart", makefile)
        self.assertIn("autostart-status", makefile)
        self.assertIn("\nboot:", makefile)
        self.assertIn("scripts/autostart.py boot", makefile)
        self.assertIn("\nrestart:", makefile)

    def test_unit_template_is_oneshot_after_docker(self) -> None:
        text = autostart.render_unit(
            workspace=Path("/data/Projects/job_search_ref"),
            user="owner",
            system=True,
        )
        self.assertIn("Type=oneshot", text)
        self.assertIn("Requires=docker.service", text)
        self.assertIn("User=owner", text)
        self.assertIn("ExecStop=", text)
        self.assertIn("make -C /data/Projects/job_search_ref down", text)
        user_text = autostart.render_unit(
            workspace=Path("/data/Projects/job_search_ref"),
            user="owner",
            system=False,
        )
        self.assertNotIn("User=owner", user_text)
        self.assertNotIn("Requires=docker.service", user_text)
        self.assertIn("WantedBy=default.target", user_text)


if __name__ == "__main__":
    unittest.main()
