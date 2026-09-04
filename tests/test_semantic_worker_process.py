"""Regression tests for self-match-safe semantic-batch work process probes."""

from __future__ import annotations

import re
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import semantic_worker_process as swp


class SemanticWorkerProcessPatternTests(unittest.TestCase):
    def test_canonical_pattern_is_self_match_safe(self) -> None:
        self.assertTrue(
            swp.pattern_is_self_match_safe(swp.SEMANTIC_BATCH_WORK_PGREP_PATTERN)
        )

    def test_unsafe_needle_is_not_self_match_safe(self) -> None:
        # This is the R2.4.5 monitor defect: pgrep -f <needle> matches itself.
        self.assertFalse(
            swp.pattern_is_self_match_safe(swp.UNSAFE_SEMANTIC_BATCH_WORK_NEEDLE)
        )
        unsafe_pgrep_argv = f"pgrep -f {swp.UNSAFE_SEMANTIC_BATCH_WORK_NEEDLE}"
        self.assertRegex(
            unsafe_pgrep_argv, re.escape(swp.UNSAFE_SEMANTIC_BATCH_WORK_NEEDLE)
        )

    def test_matches_real_worker_cmdlines(self) -> None:
        samples = [
            "python -m job_search_scoring.cli semantic-batch work --concurrency 1",
            "/usr/local/bin/python -m job_search_scoring.cli semantic-batch work",
            "python3 -m job_search_scoring.cli semantic-batch work --stop-after-terminal 35",
        ]
        for cmdline in samples:
            with self.subTest(cmdline=cmdline):
                self.assertTrue(swp.cmdline_matches_semantic_batch_work(cmdline))

    def test_does_not_match_safe_monitor_helper_or_api(self) -> None:
        samples = [
            # Safe pgrep argv embeds [p]ython…, not a real interpreter name.
            f"pgrep -f {swp.SEMANTIC_BATCH_WORK_PGREP_PATTERN}",
            (
                "bash -c while pgrep -af '[p]ython[0-9.]* -m job_search_scoring.cli "
                "semantic-batch work'; do sleep 60; done"
            ),
            "python3 scripts/semantic_worker_process.py running",
            "uvicorn job_search_scoring.api:app --host 127.0.0.1 --port 8090",
        ]
        for cmdline in samples:
            with self.subTest(cmdline=cmdline):
                self.assertFalse(swp.cmdline_matches_semantic_batch_work(cmdline))

    def test_broken_monitor_cmdline_still_contains_worker_needle(self) -> None:
        """RCA exhibit: unsafe monitor argv embeds the real worker needle.

        A leftover broken monitor can still look like a worker to any pattern
        that correctly matches ``python -m … semantic-batch work``. The fix is
        that *starting* the probe via ``pgrep -f <safe-pattern>`` must not keep
        the probe itself alive — covered by ``pattern_is_self_match_safe``.
        """
        broken = (
            "bash -c while pgrep -f 'python -m job_search_scoring.cli "
            "semantic-batch work'; do sleep 1; done"
        )
        self.assertTrue(swp.cmdline_matches_semantic_batch_work(broken))
        self.assertFalse(
            swp.pattern_is_self_match_safe(swp.UNSAFE_SEMANTIC_BATCH_WORK_NEEDLE)
        )

    def test_pgrep_argv_uses_safe_pattern_only(self) -> None:
        argv = swp.pgrep_argv()
        self.assertEqual(argv[:2], ["pgrep", "-f"])
        self.assertEqual(argv[2], swp.SEMANTIC_BATCH_WORK_PGREP_PATTERN)
        self.assertNotIn(swp.UNSAFE_SEMANTIC_BATCH_WORK_NEEDLE, " ".join(argv))

    def test_list_pids_empty_on_pgrep_exit_1(self) -> None:
        class _Result:
            returncode = 1
            stdout = ""
            stderr = ""

        with patch.object(swp.subprocess, "run", return_value=_Result()):
            self.assertEqual(swp.list_semantic_batch_work_pids(), [])

    def test_list_pids_parses_stdout(self) -> None:
        class _Result:
            returncode = 0
            stdout = "101\n202\n"
            stderr = ""

        with patch.object(swp.subprocess, "run", return_value=_Result()) as run:
            self.assertEqual(swp.list_semantic_batch_work_pids(), [101, 202])
            run.assert_called_once()
            self.assertEqual(run.call_args.args[0], swp.pgrep_argv())

    def test_makefile_wires_unit_module(self) -> None:
        makefile = (Path(__file__).resolve().parents[1] / "Makefile").read_text(
            encoding="utf-8"
        )
        self.assertIn("tests.test_semantic_worker_process", makefile)


if __name__ == "__main__":
    unittest.main()
