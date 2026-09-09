"""Unit tests for PB-DATA-01 working DB cleanup classifiers (no live DB)."""

from __future__ import annotations

import unittest

from scripts.working_db_cleanup import (
    classify_vacancy_source,
    is_acceptance_outreach_note,
    is_acceptance_search_cycle,
)


class ClassificationTests(unittest.TestCase):
    def test_vacancy_sources(self) -> None:
        self.assertEqual(classify_vacancy_source("hh"), "A_real")
        self.assertEqual(classify_vacancy_source("legacy_job_search"), "A_real")
        self.assertEqual(classify_vacancy_source("fixture"), "B_fixture")
        self.assertEqual(classify_vacancy_source("workspace-smoke"), "B_fixture")
        self.assertEqual(classify_vacancy_source("acceptance-r235"), "B_fixture")
        self.assertEqual(classify_vacancy_source("manual"), "C_ambiguous")

    def test_outreach_note_requires_explicit_prefix(self) -> None:
        self.assertTrue(
            is_acceptance_outreach_note(
                "R3.2 acceptance fixture: owner-reported contact (not sent by Job Search)"
            )
        )
        self.assertFalse(is_acceptance_outreach_note("Spoke with recruiter about salary"))
        self.assertFalse(is_acceptance_outreach_note(None))

    def test_search_cycle_acceptance_markers(self) -> None:
        self.assertTrue(
            is_acceptance_search_cycle(
                close_note="R5.2 ACCEPTANCE close search",
                offer_note=None,
                offer_title=None,
            )
        )
        self.assertTrue(
            is_acceptance_search_cycle(
                close_note=None,
                offer_note="R5.2 ACCEPTANCE winning fixture",
                offer_title="R5.2 ACCEPTANCE — Winning Offer",
            )
        )
        self.assertFalse(
            is_acceptance_search_cycle(
                close_note="Accepted real offer and closed search",
                offer_note="Real company package",
                offer_title="Staff Engineer",
            )
        )


if __name__ == "__main__":
    unittest.main()
