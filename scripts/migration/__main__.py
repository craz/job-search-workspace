"""CLI entrypoint for legacy migration dry-run."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from scripts.migration.constants import DEFAULT_LEGACY_ROOT
from scripts.migration.dry_run import discover_default_target_url, run_dry_run


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run legacy migration dry-run with zero target mutation.")
    parser.add_argument(
        "command",
        choices=["dry-run"],
        help="Only dry-run is supported in DATA-00.4.",
    )
    parser.add_argument(
        "--legacy-root",
        type=Path,
        default=DEFAULT_LEGACY_ROOT,
        help="Read-only legacy source root.",
    )
    parser.add_argument(
        "--target-url",
        default=None,
        help="Core PostgreSQL URL for read-only inspection.",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=None,
        help="Directory for backups/migration-runs artifacts.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    workspace_root = Path(__file__).resolve().parents[2]
    target_url = args.target_url or discover_default_target_url()
    if not target_url:
        print("Target database URL is required; set JOB_SEARCH_CORE_DATABASE_URL or start compose postgres.", file=sys.stderr)
        return 2
    run_dir, counts_before, counts_after, success = run_dry_run(
        workspace_root=workspace_root,
        legacy_root=args.legacy_root,
        target_database_url=target_url,
        output_root=args.output_root,
    )
    print(run_dir)
    print(f"target_counts_before={counts_before}")
    print(f"target_counts_after={counts_after}")
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
