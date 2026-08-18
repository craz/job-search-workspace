"""Unit coverage for the bounded public Compose smoke workflow."""

from __future__ import annotations

import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from scripts import compose_smoke


class ComposeSmokeTests(unittest.TestCase):
    """Validate success and failure decisions without network or Docker access."""

    @patch("scripts.compose_smoke.request")
    def test_success_requires_create_update_and_persisted_list(self, request_mock) -> None:
        """A complete public flow exits zero and emits one machine-readable result."""
        vacancy_id = "00000000-0000-0000-0000-000000000042"
        request_mock.side_effect = [
            (201, {"id": vacancy_id, "status": "new"}),
            (200, {"id": vacancy_id, "status": "reviewing"}),
            (200, {"items": [{"id": vacancy_id}], "total": 1}),
        ]
        output = io.StringIO()

        with redirect_stdout(output):
            result = compose_smoke.main()

        self.assertEqual(result, 0)
        self.assertTrue(json.loads(output.getvalue())["ok"])
        self.assertEqual(request_mock.call_count, 3)

    @patch("scripts.compose_smoke.request")
    def test_incomplete_flow_exits_nonzero(self, request_mock) -> None:
        """Missing persistence evidence cannot be reported as a successful smoke."""
        request_mock.side_effect = [
            (201, {"id": "fixture", "status": "new"}),
            (200, {"id": "fixture", "status": "reviewing"}),
            (200, {"items": [], "total": 0}),
        ]

        with redirect_stdout(io.StringIO()):
            result = compose_smoke.main()

        self.assertEqual(result, 1)


if __name__ == "__main__":
    unittest.main()
