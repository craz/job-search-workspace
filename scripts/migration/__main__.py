"""CLI entrypoint for legacy migration dry-run and APPLY."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from scripts.migration.apply import run_apply
from scripts.migration.constants import DEFAULT_LEGACY_ROOT
from scripts.migration.dry_run import discover_default_target_url, run_dry_run


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Legacy migration dry-run and bounded APPLY.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    dry_run = subparsers.add_parser("dry-run", help="Zero-mutation migration plan and report.")
    dry_run.add_argument(
        "--legacy-root",
        type=Path,
        default=DEFAULT_LEGACY_ROOT,
        help="Read-only legacy source root.",
    )
    dry_run.add_argument(
        "--target-url",
        default=None,
        help="Core PostgreSQL URL for read-only inspection.",
    )
    dry_run.add_argument(
        "--output-root",
        type=Path,
        default=None,
        help="Directory for backups/migration-runs artifacts.",
    )

    apply_cmd = subparsers.add_parser("apply", help="Mutating APPLY bound to one verified dry-run.")
    apply_cmd.add_argument(
        "--run-id",
        required=True,
        help="Verified dry-run run_id directory under backups/migration-runs/.",
    )
    apply_cmd.add_argument(
        "--legacy-root",
        type=Path,
        default=DEFAULT_LEGACY_ROOT,
        help="Read-only legacy source root.",
    )
    apply_cmd.add_argument(
        "--target-url",
        default=None,
        help="Core PostgreSQL URL for APPLY.",
    )
    apply_cmd.add_argument(
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

    if args.command == "dry-run":
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

    run_dir, success = run_apply(
        workspace_root=workspace_root,
        dry_run_id=args.run_id,
        legacy_root=args.legacy_root,
        target_database_url=target_url,
        output_root=args.output_root,
    )
    print(run_dir)
    print(f"apply_success={success}")
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
