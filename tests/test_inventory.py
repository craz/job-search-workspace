"""Tests for deterministic ownership of archived source files."""

from __future__ import annotations

import unittest
from pathlib import Path

from scripts.check_inventory import (
    DEFAULT_LOCK,
    DEFERRED_OWNER,
    PRODUCT_OWNERS,
    audit,
    classify,
    verify_lock,
)


class ClassificationTests(unittest.TestCase):
    """Protect representative subsystem boundaries from accidental drift."""

    def test_representative_paths_have_expected_owners(self) -> None:
        """Each major subsystem and deferred scope resolves deterministically."""
        examples = {
            "src/job_search/models.py": "job-search-core",
            "src/job_search/hh_browser.py": "job-search-hh",
            "src/job_search/ollama_scoring.py": "job-search-scoring",
            "src/job_search/osint/pipeline.py": "job-search-osint",
            "src/job_search/telegram_bot.py": "job-search-content",
            "src/job_search/server.py": "job-search-web",
            "src/job_search/hermes_bridge.py": DEFERRED_OWNER,
        }
        self.assertEqual(examples, {path: classify(path).owner for path in examples})

    def test_current_archive_has_one_valid_owner_per_code_file(self) -> None:
        """The actual read-only snapshot must contain no ownership gaps."""
        source = Path("/data/Projects/job_search")
        if not source.is_dir():
            self.skipTest("local archived source is not available")
        assignments = audit(source)
        self.assertEqual(len(assignments), len({item.path for item in assignments}))
        self.assertTrue(assignments)
        self.assertTrue({item.owner for item in assignments} <= PRODUCT_OWNERS | {DEFERRED_OWNER})
        verify_lock(source, assignments, DEFAULT_LOCK)

    def test_unknown_path_is_rejected_instead_of_defaulting_to_core(self) -> None:
        """A newly discovered module must require an explicit ownership decision."""
        with self.assertRaisesRegex(ValueError, "unclassified source module"):
            classify("src/job_search/new_mixed_feature.py")


if __name__ == "__main__":
    unittest.main()
