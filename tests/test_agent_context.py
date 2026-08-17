"""Regression tests for bounded Codex and Cursor instruction context."""

from __future__ import annotations

import re
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
RULES = ROOT / ".cursor" / "rules"


def frontmatter_value(rule: Path, key: str) -> str | None:
    """Read one scalar MDC frontmatter value without adding a YAML dependency.

    The gate only needs scalar ``alwaysApply`` values. Returning ``None`` for an
    absent key makes malformed or ambiguous rules fail explicit assertions.
    """
    match = re.search(rf"(?m)^{re.escape(key)}:\s*([^\n]+)$", rule.read_text(encoding="utf-8"))
    return match.group(1).strip() if match else None


class CursorContextTests(unittest.TestCase):
    """Keep global instructions small and private/generated content excluded."""

    def test_only_one_cursor_rule_is_always_applied(self) -> None:
        """A new global rule must be merged into the minimal global source."""
        always = [
            rule.name
            for rule in RULES.glob("*.mdc")
            if frontmatter_value(rule, "alwaysApply") == "true"
        ]

        self.assertEqual(["00-project-context.mdc"], sorted(always))

    def test_private_ai_history_is_excluded_from_cursor_requests(self) -> None:
        """Canonical sessions and summaries must not become automatic AI context."""
        patterns = (ROOT / ".cursorignore").read_text(encoding="utf-8")

        for required in (".local/sessions/", ".local/derived/", ".local/AI_HISTORY.md"):
            self.assertIn(required, patterns)

    def test_heavy_local_trees_are_excluded_from_semantic_index(self) -> None:
        """Environment, runtime and generated trees must not consume index space."""
        patterns = (ROOT / ".cursorindexingignore").read_text(encoding="utf-8")

        for required in (".venv/", ".local/", "data/", "generated/", "vendor/"):
            self.assertIn(required, patterns)

    def test_end_of_turn_hooks_share_the_safe_history_wrapper(self) -> None:
        """Codex and Cursor must synchronize through the same reviewed script."""
        cursor = json.loads((ROOT / ".cursor/hooks.json").read_text())
        codex = json.loads((ROOT / ".codex/hooks.json").read_text())

        cursor_hook = cursor["hooks"]["stop"][0]
        codex_hook = codex["hooks"]["Stop"][0]["hooks"][0]
        self.assertIn("scripts/ai_history_hook.py", cursor_hook["command"])
        self.assertIn("scripts/ai_history_hook.py", codex_hook["command"])
        self.assertFalse(cursor_hook["failClosed"])
        self.assertEqual("command", codex_hook["type"])


if __name__ == "__main__":
    unittest.main()
