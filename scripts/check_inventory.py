#!/usr/bin/env python3
"""Prove that every archived monolith source file has one product owner.

The checker optionally reads a historical local snapshot of the original
monolith without modifying it. It is a workspace bootstrap inventory, not a
runtime or setup dependency of Job Search. `make test` skips the live-archive
check when that snapshot is absent.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence


DEFAULT_SOURCE = Path("/data/Projects/job_search")
DEFAULT_LOCK = Path(__file__).resolve().parent.parent / "docs/inventory/source-code.lock.json"
PRODUCT_OWNERS = {
    "job-search-core",
    "job-search-hh",
    "job-search-scoring",
    "job-search-osint",
    "job-search-content",
    "job-search-web",
}
DEFERRED_OWNER = "deferred-local"
CORE_MODULES = {
    "__init__.py",
    "application/__init__.py",
    "application/vacancies.py",
    "cli.py",
    "cohorts.py",
    "company_card.py",
    "company_cli.py",
    "config.py",
    "db.py",
    "domain/__init__.py",
    "domain/vacancy_rules.py",
    "http_client.py",
    "infrastructure/__init__.py",
    "infrastructure/db/__init__.py",
    "infrastructure/db/migrations/__init__.py",
    "infrastructure/db/repositories/__init__.py",
    "infrastructure/db/repositories/applications.py",
    "infrastructure/db/repositories/companies.py",
    "infrastructure/db/repositories/daily_metrics.py",
    "infrastructure/db/repositories/hypotheses.py",
    "infrastructure/db/repositories/people.py",
    "infrastructure/db/repositories/settings.py",
    "infrastructure/db/repositories/vacancies.py",
    "infrastructure/db/rows.py",
    "infrastructure/paths.py",
    "interfaces/__init__.py",
    "interfaces/cli/__init__.py",
    "interfaces/cli/core.py",
    "interfaces/cli/hypothesis.py",
    "interfaces/cli/vacancy.py",
    "metrics_cli.py",
    "migrate_cli.py",
    "models.py",
    "people_cli.py",
    "statuses.py",
}
CORE_TESTS = {
    "conftest.py",
    "test_application_vacancies.py",
    "test_config.py",
    "test_migrations.py",
    "test_rejections_metrics.py",
    "test_repositories.py",
    "test_statuses.py",
    "test_vacancy_repository.py",
    "test_vacancy_rules.py",
}


@dataclass(frozen=True)
class Assignment:
    """One source path, its sole migration owner and matching rationale."""

    path: str
    owner: str
    reason: str


def discover_code(source: Path) -> list[str]:
    """Return migration-relevant code paths from the current archive.

    Runtime data, fixtures, environments and generated files are excluded because
    the data migration plan owns them. Missing expected directories are errors:
    silently checking an empty snapshot would create a false green gate.
    """
    expected = (source / "src" / "job_search", source / "tests", source / "scripts")
    missing = [str(path) for path in expected if not path.is_dir()]
    if missing:
        raise ValueError(f"missing source directories: {', '.join(missing)}")

    paths = {
        path.relative_to(source).as_posix()
        for path in (source / "src" / "job_search").rglob("*.py")
    }
    paths.update(path.relative_to(source).as_posix() for path in (source / "tests").glob("*.py"))
    paths.update(
        path.relative_to(source).as_posix()
        for path in (source / "scripts").iterdir()
        if path.is_file() and path.suffix in {".py", ".sh"}
    )
    paths.update(
        path.relative_to(source).as_posix()
        for path in source.iterdir()
        if path.is_file() and path.suffix == ".py"
    )
    return sorted(paths)


def classify_source_module(relative: str) -> Assignment:
    """Assign one application module using architectural subsystem boundaries.

    Dedicated service and deferred namespaces are recognized first. Core paths
    are then accepted from an explicit allowlist. There is intentionally no
    catch-all: a newly discovered module must fail until its owner is reviewed.
    """
    module = relative.removeprefix("src/job_search/")
    if module.startswith("osint/") or module in {"osint_cli.py", "company_resolve.py"}:
        return Assignment(relative, "job-search-osint", "OSINT discovery and provenance")
    if module.startswith("interfaces/views/") or module in {
        "board.py", "board_bg.py", "server.py", "vacancy_scoring_board.py",
    }:
        return Assignment(relative, "job-search-web", "browser board or legacy mixed web server")
    if module.startswith("application/hh_") or module.startswith("hh_") or module in {
        "apply_many_log.py", "apply_tick_log.py", "interfaces/cli/hh.py", "vacancy_fetch_pool.py",
    }:
        return Assignment(relative, "job-search-hh", "HH integration, browser or apply workflow")
    if module.startswith(("ollama_", "score_", "vacancy_scoring")) or module in {
        "assessment_note.py", "resume_text.py",
    }:
        return Assignment(relative, "job-search-scoring", "vacancy assessment or Ollama workflow")
    if module.startswith(("telegram_", "cover_")) or module in {
        "application/drafts.py", "interfaces/cli/content.py", "interfaces/cli/draft.py",
        "interfaces/cli/report.py", "interfaces/cli/telegram.py", "reports.py",
        "infrastructure/db/repositories/content_logs.py",
    }:
        return Assignment(relative, "job-search-content", "draft, report or Telegram workflow")
    if module.startswith("hermes_") or module in {
        "hirer_cli.py", "interfaces/cli/hermes.py", "parse_cli.py",
        "recommend_catalog.py", "recommend_cli.py",
    }:
        return Assignment(relative, DEFERRED_OWNER, "deferred Hermes or legacy local workflow")
    if module in CORE_MODULES:
        return Assignment(relative, "job-search-core", "domain, persistence or Core interface")
    raise ValueError(f"unclassified source module: {relative}")


def classify_test(relative: str) -> Assignment:
    """Assign a test to the service that must preserve the tested behavior."""
    name = Path(relative).name
    if name.startswith("test_osint_") or name == "test_people_company_resolve.py":
        return Assignment(relative, "job-search-osint", "OSINT behavior")
    if name.startswith("test_hermes_") or name == "test_extract_chat_signals_cli.py":
        return Assignment(relative, DEFERRED_OWNER, "deferred local integration")
    if name.startswith(("test_ollama_", "test_score_", "test_vacancy_scoring")) or name in {
        "test_assessment_note.py", "test_hh_score_vacancy_cli.py",
        "test_verdict_override.py", "test_write_chatgpt_prompts.py",
    }:
        return Assignment(relative, "job-search-scoring", "scoring behavior")
    if name.startswith("test_hh_") or name in {
        "test_apply_many_log.py", "test_apply_tick_log.py", "test_oauth_callback.py",
        "test_resume_view_history_parser.py", "test_resume_views.py", "test_vacancy_fetch_pool.py",
    }:
        return Assignment(relative, "job-search-hh", "HH integration behavior")
    if name.startswith("test_board_") or name in {
        "test_apply_form.py", "test_server_api.py", "test_server_applications.py",
        "test_server_resume_views.py",
    }:
        return Assignment(relative, "job-search-web", "web board or legacy server behavior")
    if name.startswith("test_telegram_") or name == "test_cover_letter.py":
        return Assignment(relative, "job-search-content", "content or Telegram behavior")
    if name in CORE_TESTS:
        return Assignment(relative, "job-search-core", "Core domain or persistence behavior")
    raise ValueError(f"unclassified test: {relative}")


def classify_script(relative: str) -> Assignment:
    """Assign operational and root scripts without executing their contents."""
    name = Path(relative).name
    if name in {"fetch-all-bg.sh", "hh-chrome-cdp.sh", "solve_captcha_tg_once.py"}:
        return Assignment(relative, "job-search-hh", "HH operational script")
    if name in {
        "ollama-scorer-install.sh", "rescore-rules-bg.sh", "score-ollama-bg.sh",
        "write-chatgpt-prompts.sh",
    }:
        return Assignment(relative, "job-search-scoring", "scoring operational script")
    if name == "fetch_board_bg.py":
        return Assignment(relative, "job-search-web", "web asset tooling")
    if name in {"hermes-bridge-install.sh", "extract_chat_signals.py", "convert_chatgpt_export.py"}:
        return Assignment(relative, DEFERRED_OWNER, "deferred local utility")
    if name in {"_snap_other_country.py", "ensure-venv.sh"}:
        return Assignment(relative, DEFERRED_OWNER, "legacy or shared bootstrap utility")
    raise ValueError(f"unclassified operational script: {relative}")


def classify(relative: str) -> Assignment:
    """Route one discovered path through exactly one ownership decision tree."""
    if relative.startswith("src/job_search/"):
        return classify_source_module(relative)
    if relative.startswith("tests/"):
        return classify_test(relative)
    if relative.startswith("scripts/") or "/" not in relative:
        return classify_script(relative)
    raise ValueError(f"unclassified code path: {relative}")


def audit(source: Path) -> list[Assignment]:
    """Discover and classify the snapshot, rejecting invalid owner identifiers."""
    assignments = [classify(path) for path in discover_code(source)]
    allowed = PRODUCT_OWNERS | {DEFERRED_OWNER}
    invalid = [item for item in assignments if item.owner not in allowed]
    if invalid:
        raise ValueError(f"invalid owners: {[item.owner for item in invalid]}")
    return assignments


def snapshot_digest(source: Path, assignments: Sequence[Assignment]) -> str:
    """Hash ordered paths and bytes so renames and content changes alter the lock.

    Null separators make the aggregate unambiguous even when one filename is a
    prefix of another. Only files admitted by the ownership audit participate.
    """
    digest = hashlib.sha256()
    for item in assignments:
        digest.update(item.path.encode("utf-8"))
        digest.update(b"\0")
        digest.update((source / item.path).read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def verify_lock(source: Path, assignments: Sequence[Assignment], lock_path: Path) -> None:
    """Reject source drift against the reviewed file count and aggregate digest."""
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    if lock.get("schema_version") != 1:
        raise ValueError("unsupported inventory lock schema_version")
    if lock.get("file_count") != len(assignments):
        raise ValueError(
            f"source file count {len(assignments)} differs from lock {lock.get('file_count')}"
        )
    actual = snapshot_digest(source, assignments)
    if lock.get("sha256") != actual:
        raise ValueError(f"source digest {actual} differs from lock {lock.get('sha256')}")


def build_parser() -> argparse.ArgumentParser:
    """Define source selection and optional machine-readable report output."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--lock", type=Path, default=DEFAULT_LOCK)
    parser.add_argument("--json", action="store_true", help="print every assignment as JSON")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the ownership gate and return 1 for an unreadable or invalid snapshot."""
    args = build_parser().parse_args(argv)
    try:
        source = args.source.resolve()
        assignments = audit(source)
        verify_lock(source, assignments, args.lock.resolve())
    except (OSError, ValueError) as error:
        print(f"[ERROR] inventory: {error}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps([asdict(item) for item in assignments], ensure_ascii=False, indent=2))
    counts: dict[str, int] = {}
    for item in assignments:
        counts[item.owner] = counts.get(item.owner, 0) + 1
    print(f"[OK] inventory: {len(assignments)} code files have exactly one owner")
    for owner, count in sorted(counts.items()):
        print(f"[OK] {owner}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
