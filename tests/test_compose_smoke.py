"""Unit coverage for the bounded public Compose smoke workflow."""

from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from scripts import compose_smoke


class ComposeSmokeTests(unittest.TestCase):
    """Validate success and failure decisions without network or Docker access."""

    @patch("scripts.compose_smoke.request")
    def test_success_requires_all_tracking_entities_to_persist(self, request_mock) -> None:
        """A complete public flow exits zero and emits one machine-readable result."""
        vacancy_id = "00000000-0000-0000-0000-000000000042"
        application_id = "00000000-0000-0000-0000-000000000044"
        person_id = "00000000-0000-0000-0000-000000000045"
        request_mock.side_effect = [
            (201, {"id": vacancy_id, "status": "new", "company": {"id": "company-43"}}),
            (200, {"id": vacancy_id, "status": "reviewing"}),
            (200, {"items": [{"id": vacancy_id}], "total": 1}),
            (201, {"id": application_id, "vacancy": {"id": vacancy_id}}),
            (200, {"items": [{"id": application_id}], "total": 1}),
            (201, {"metric_date": "2026-08-20", "applications": 1}),
            (200, {"items": [{"metric_date": "2026-08-20"}], "total": 1}),
            (201, {"id": person_id, "vacancy": {"id": vacancy_id}, "status": "new"}),
            (200, {"id": person_id, "status": "researching"}),
            (200, {"items": [{"id": person_id}], "total": 1}),
        ]
        output = io.StringIO()

        with redirect_stdout(output):
            result = compose_smoke.main()

        self.assertEqual(result, 0)
        self.assertTrue(json.loads(output.getvalue())["ok"])
        self.assertEqual(request_mock.call_count, 10)

    @patch("scripts.compose_smoke.request")
    def test_incomplete_flow_exits_nonzero(self, request_mock) -> None:
        """Missing persistence evidence cannot be reported as a successful smoke."""
        request_mock.side_effect = [
            (201, {"id": "fixture", "status": "new"}),
            (200, {"id": "fixture", "status": "reviewing"}),
            (200, {"items": [], "total": 0}),
            (201, {"id": "application", "vacancy": {"id": "fixture"}}),
            (200, {"items": [{"id": "application"}], "total": 1}),
            (201, {"metric_date": "2026-08-20", "applications": 1}),
            (200, {"items": [{"metric_date": "2026-08-20"}], "total": 1}),
            (201, {"id": "person", "vacancy": {"id": "fixture"}, "status": "new"}),
            (200, {"id": "person", "status": "researching"}),
            (200, {"items": [{"id": "person"}], "total": 1}),
        ]

        with redirect_stdout(io.StringIO()):
            result = compose_smoke.main()

        self.assertEqual(result, 1)

    def test_make_exports_local_compose_ports_to_smoke(self) -> None:
        """A port override used by Compose must also select the smoke endpoint."""
        makefile = (Path(__file__).parents[1] / "Makefile").read_text(encoding="utf-8")

        self.assertIn("-include .env", makefile)
        self.assertIn("export CORE_PORT WEB_PORT", makefile)

    def test_dev_compose_mounts_sources_and_enables_reload(self) -> None:
        """The documented make dev loop must observe code and refresh processes."""
        compose = (Path(__file__).parents[1] / "compose.yaml").read_text(encoding="utf-8")

        self.assertIn("./services/core/src:/app/src:ro", compose)
        self.assertIn("./services/web/src:/app/src:ro", compose)
        self.assertEqual(compose.count("--reload --reload-dir"), 1)
        self.assertEqual(compose.splitlines().count("      - --reload"), 1)
        self.assertIn('WEB_LIVE_RELOAD: "1"', compose)


if __name__ == "__main__":
    unittest.main()
