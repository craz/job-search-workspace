#!/usr/bin/env python3
"""Self-match-safe detection of the canonical semantic-batch work CLI process.

Operator monitors that use naive::

    pgrep -f 'python -m job_search_scoring.cli semantic-batch work'

self-match: the monitoring shell's own argv contains that exact needle, so
``pgrep`` keeps finding the monitor after the real worker has exited
(R2.4.5 RCA).

The canonical pattern uses a one-character class on the leading letter so the
regex matches a real ``python …`` worker cmdline but does **not** match the
literal ``[p]ython …`` text embedded in the monitor / ``pgrep`` argv::

    pgrep -f '[p]ython[0-9.]* -m job_search_scoring\\.cli semantic-batch work'

This module owns that pattern and the ``pgrep`` invocation so operational
tooling does not reintroduce the unsafe needle.

Usage::

    python3 scripts/semantic_worker_process.py pids
    python3 scripts/semantic_worker_process.py running   # exit 0 if any PIDs
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys

# Bracket trick: character class ``[p]`` still matches ``p`` in a real worker
# argv (``python`` / ``python3`` …), but a process whose argv literally contains
# ``[p]ython`` (the monitor / this helper) does not match.
SEMANTIC_BATCH_WORK_PGREP_PATTERN = (
    r"[p]ython[0-9.]* -m job_search_scoring\.cli semantic-batch work"
)

# Naive needle that MUST NOT be used with ``pgrep -f`` in operator loops.
UNSAFE_SEMANTIC_BATCH_WORK_NEEDLE = (
    "python -m job_search_scoring.cli semantic-batch work"
)

_PATTERN_RE = re.compile(SEMANTIC_BATCH_WORK_PGREP_PATTERN)


def pgrep_argv() -> list[str]:
    """Return argv for a self-match-safe worker existence probe."""
    return ["pgrep", "-f", SEMANTIC_BATCH_WORK_PGREP_PATTERN]


def cmdline_matches_semantic_batch_work(cmdline: str) -> bool:
    """True when *cmdline* looks like the canonical semantic-batch work CLI."""
    return _PATTERN_RE.search(cmdline) is not None


def pattern_is_self_match_safe(pattern: str) -> bool:
    """True when ``pgrep -f <pattern>`` cannot match its own argv string.

    A pattern that appears verbatim inside ``pgrep -f <pattern>`` will keep a
    monitor loop alive forever after the real worker exits.
    """
    probe_argv = f"pgrep -f {pattern}"
    return re.search(pattern, probe_argv) is None


def list_semantic_batch_work_pids() -> list[int]:
    """Return PIDs of running semantic-batch work processes, or ``[]`` if none.

    Uses the self-match-safe pattern. Does not signal or kill processes.
    """
    completed = subprocess.run(
        pgrep_argv(),
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode not in (0, 1):
        raise RuntimeError(
            f"pgrep failed (exit {completed.returncode}): "
            f"{(completed.stderr or completed.stdout or '').strip()}"
        )
    if completed.returncode == 1 or not completed.stdout.strip():
        return []
    pids: list[int] = []
    for line in completed.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        pids.append(int(line))
    return pids


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Self-match-safe semantic-batch work process probe"
    )
    parser.add_argument(
        "command",
        choices=("pids", "running", "pattern"),
        help="pids: print PIDs; running: exit 0/1; pattern: print pgrep -f pattern",
    )
    args = parser.parse_args(argv)

    if args.command == "pattern":
        print(SEMANTIC_BATCH_WORK_PGREP_PATTERN)
        return 0

    if not pattern_is_self_match_safe(SEMANTIC_BATCH_WORK_PGREP_PATTERN):
        print(
            "error: canonical pattern is not self-match-safe",
            file=sys.stderr,
        )
        return 2

    pids = list_semantic_batch_work_pids()
    if args.command == "pids":
        for pid in pids:
            print(pid)
        return 0

    # running
    return 0 if pids else 1


if __name__ == "__main__":
    raise SystemExit(main())
