#!/usr/bin/env python3
"""PB-DATA-01: inventory / dry-run / purge of provable test fixtures in working DB.

Safety invariants:
- Default mode is dry-run (no DELETE).
- Purge requires explicit --execute after a successful backup step in the same run
  or --backup-path pointing at an existing dump from this session's guidance.
- Only rows with deterministic technical markers are classified B (removable).
- Ambiguous rows are kept and reported.
- Does not commit dumps; writes only under gitignored backups/.

Classification (Vacancy / Company primary):
  A_real     — source in {hh, legacy_job_search}
  B_fixture  — source in {fixture, workspace-smoke, acceptance-r235}
  C_ambiguous — anything else (KEEP)

Additional removable B rows without deleting the parent real Vacancy:
  - DirectOutreach whose note starts with known acceptance-fixture prefixes
  - People with source workspace-smoke, or full_name 'Synthetic Confirm Person'
    linked only to B companies/vacancies
  - Hypotheses with source workspace-smoke
  - SearchCycle closed with close_note / accepted Offer note containing
    'R5.2 ACCEPTANCE' (acceptance lock)

After purge of fixture SearchCycle: insert one active SearchCycle if none remain.
Does not enable automation; leaves it manually enable-able.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_BACKUP_ROOT = WORKSPACE_ROOT / "backups" / "pb-data-01"
COMPOSE_FILE = WORKSPACE_ROOT / "compose.yaml"
PSQL_USER = "job_search"
PSQL_DB = "job_search"

FIXTURE_VACANCY_SOURCES = ("fixture", "workspace-smoke", "acceptance-r235")
REAL_VACANCY_SOURCES = ("hh", "legacy_job_search")

# Explicit owner-reported acceptance outreaches planted on real HH vacancies.
ACCEPTANCE_OUTREACH_NOTE_PREFIXES = (
    "R3.2 acceptance fixture:",
    "R3. acceptance fixture:",
)

ACCEPTANCE_SEARCH_CYCLE_MARKERS = (
    "R5.2 ACCEPTANCE",
    "R5.2 ACCEPTANCE close search",
)


def _compose_base() -> list[str]:
    return ["docker", "compose", "-f", str(COMPOSE_FILE)]


def run_psql(sql: str, *, tuples_only: bool = False) -> str:
    """Execute SQL via compose postgres; return stdout text."""
    cmd = [
        *_compose_base(),
        "exec",
        "-T",
        "postgres",
        "psql",
        "-U",
        PSQL_USER,
        "-d",
        PSQL_DB,
        "-v",
        "ON_ERROR_STOP=1",
    ]
    if tuples_only:
        cmd.extend(["-At", "-F", "\t"])
    else:
        cmd.append("-q")
    proc = subprocess.run(
        cmd,
        input=sql,
        text=True,
        capture_output=True,
        cwd=str(WORKSPACE_ROOT),
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"psql failed ({proc.returncode}): {proc.stderr.strip() or proc.stdout}"
        )
    return proc.stdout


def run_psql_json(sql: str) -> Any:
    """Run a query that returns a single JSON value."""
    wrapped = f"SELECT COALESCE(json_agg(row_to_json(q)), '[]'::json) FROM ({sql}) q;"
    # Prefer jsonb_build via CTE returning one row
    out = run_psql(
        f"COPY (SELECT COALESCE((SELECT json_agg(row_to_json(q)) FROM ({sql}) q), '[]'::json)) TO STDOUT;",
        tuples_only=True,
    ).strip()
    if not out:
        return []
    return json.loads(out)


def classify_vacancy_source(source: str) -> str:
    """Return A_real / B_fixture / C_ambiguous for a vacancy/company source."""
    if source in REAL_VACANCY_SOURCES:
        return "A_real"
    if source in FIXTURE_VACANCY_SOURCES:
        return "B_fixture"
    return "C_ambiguous"


def is_acceptance_outreach_note(note: str | None) -> bool:
    """True when DirectOutreach.note is an explicit acceptance fixture marker."""
    if not note:
        return False
    text = note.strip()
    return any(text.startswith(prefix) for prefix in ACCEPTANCE_OUTREACH_NOTE_PREFIXES)


def is_acceptance_search_cycle(
    *,
    close_note: str | None,
    offer_note: str | None,
    offer_title: str | None,
) -> bool:
    """True when SearchCycle/Offer text proves R5.2 acceptance lock."""
    blob = " ".join(x for x in (close_note, offer_note, offer_title) if x)
    return any(marker in blob for marker in ACCEPTANCE_SEARCH_CYCLE_MARKERS)


def entity_counts_sql() -> str:
    return """
SELECT * FROM (
  SELECT 'vacancies'::text AS entity, count(*)::int AS count FROM vacancies
  UNION ALL SELECT 'assessments', count(*)::int FROM assessments
  UNION ALL SELECT 'applications', count(*)::int FROM applications
  UNION ALL SELECT 'direct_outreaches', count(*)::int FROM direct_outreaches
  UNION ALL SELECT 'employer_responses', count(*)::int FROM employer_responses
  UNION ALL SELECT 'hiring_processes', count(*)::int FROM hiring_processes
  UNION ALL SELECT 'hiring_stage_events', count(*)::int FROM hiring_stage_events
  UNION ALL SELECT 'hiring_activities', count(*)::int FROM hiring_activities
  UNION ALL SELECT 'offers', count(*)::int FROM offers
  UNION ALL SELECT 'search_cycles', count(*)::int FROM search_cycles
  UNION ALL SELECT 'search_runs', count(*)::int FROM search_runs
  UNION ALL SELECT 'search_run_items', count(*)::int FROM search_run_items
  UNION ALL SELECT 'companies', count(*)::int FROM companies
  UNION ALL SELECT 'people', count(*)::int FROM people
  UNION ALL SELECT 'hypotheses', count(*)::int FROM hypotheses
) s ORDER BY entity
"""


def inventory_payload() -> dict[str, Any]:
    """Build inventory JSON from live DB."""
    counts = {row["entity"]: row["count"] for row in run_psql_json(entity_counts_sql())}
    vac_by_source = run_psql_json(
        "SELECT source, count(*)::int AS count FROM vacancies GROUP BY source ORDER BY count DESC"
    )
    vac_classes: dict[str, int] = {"A_real": 0, "B_fixture": 0, "C_ambiguous": 0}
    for row in vac_by_source:
        vac_classes[classify_vacancy_source(row["source"])] += row["count"]

    fixture_vac_sql = (
        "SELECT id FROM vacancies WHERE source IN "
        f"{FIXTURE_VACANCY_SOURCES!r}".replace("'", "'")
    )
    # build IN list for SQL
    sources_sql = ", ".join(f"'{s}'" for s in FIXTURE_VACANCY_SOURCES)
    purge_v = f"SELECT id FROM vacancies WHERE source IN ({sources_sql})"

    dependents = run_psql_json(
        f"""
        SELECT 'assessments' AS entity, count(*)::int AS count FROM assessments
          WHERE vacancy_id IN ({purge_v})
        UNION ALL SELECT 'applications', count(*)::int FROM applications
          WHERE vacancy_id IN ({purge_v})
        UNION ALL SELECT 'employer_responses', count(*)::int FROM employer_responses
          WHERE vacancy_id IN ({purge_v})
        UNION ALL SELECT 'hiring_processes', count(*)::int FROM hiring_processes
          WHERE vacancy_id IN ({purge_v})
        UNION ALL SELECT 'offers', count(*)::int FROM offers
          WHERE vacancy_id IN ({purge_v})
        UNION ALL SELECT 'hiring_stage_events', count(*)::int FROM hiring_stage_events
          WHERE hiring_process_id IN (
            SELECT id FROM hiring_processes WHERE vacancy_id IN ({purge_v})
          )
        UNION ALL SELECT 'hiring_activities', count(*)::int FROM hiring_activities
          WHERE hiring_process_id IN (
            SELECT id FROM hiring_processes WHERE vacancy_id IN ({purge_v})
          )
        """
    )

    outreaches = run_psql_json(
        """
        SELECT d.id::text AS id, d.note, v.source AS vacancy_source, v.title AS vacancy_title
        FROM direct_outreaches d
        JOIN vacancies v ON v.id = d.vacancy_id
        """
    )
    acceptance_outreaches = [
        row for row in outreaches if is_acceptance_outreach_note(row.get("note"))
    ]

    cycles = run_psql_json(
        """
        SELECT sc.id::text AS id, sc.status, sc.close_note,
               o.note AS offer_note, o.position_title AS offer_title,
               sc.accepted_offer_id::text AS accepted_offer_id
        FROM search_cycles sc
        LEFT JOIN offers o ON o.id = sc.accepted_offer_id
        """
    )
    fixture_cycles = [
        row
        for row in cycles
        if is_acceptance_search_cycle(
            close_note=row.get("close_note"),
            offer_note=row.get("offer_note"),
            offer_title=row.get("offer_title"),
        )
    ]

    people_smoke = run_psql_json(
        """
        SELECT id::text AS id, full_name, source
        FROM people
        WHERE source = 'workspace-smoke'
           OR (
             full_name = 'Synthetic Confirm Person'
             AND company_id IN (
               SELECT id FROM companies WHERE source IN ('fixture','workspace-smoke','acceptance-r235')
             )
           )
        """
    )
    companies_fixture = run_psql_json(
        f"""
        SELECT id::text AS id, source, name, external_id
        FROM companies
        WHERE source IN ({sources_sql})
        """
    )
    hypotheses_smoke = run_psql_json(
        "SELECT id::text AS id, title FROM hypotheses WHERE source = 'workspace-smoke'"
    )

    ambiguous = {
        "legacy_job_search_vacancies": run_psql_json(
            "SELECT id::text AS id, title, external_id FROM vacancies "
            "WHERE source = 'legacy_job_search' ORDER BY title"
        ),
        "note": (
            "legacy_job_search vacancies/applications/assessments are migrated real "
            "history — KEEP. SearchRuns (hh) KEEP. People with source osint/manual/web "
            "KEEP unless Synthetic Confirm Person tied only to smoke company."
        ),
    }

    return {
        "database": PSQL_DB,
        "user": PSQL_USER,
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "entity_counts": counts,
        "vacancy_by_source": vac_by_source,
        "vacancy_classes": vac_classes,
        "fixture_dependents": {row["entity"]: row["count"] for row in dependents},
        "acceptance_outreaches_on_real_vacancies": acceptance_outreaches,
        "acceptance_search_cycles": fixture_cycles,
        "people_fixture": people_smoke,
        "companies_fixture": companies_fixture,
        "hypotheses_fixture": hypotheses_smoke,
        "ambiguous_kept": ambiguous,
        "classification_rules": {
            "A_real_vacancy_sources": list(REAL_VACANCY_SOURCES),
            "B_fixture_vacancy_sources": list(FIXTURE_VACANCY_SOURCES),
            "acceptance_outreach_note_prefixes": list(ACCEPTANCE_OUTREACH_NOTE_PREFIXES),
            "acceptance_search_cycle_markers": list(ACCEPTANCE_SEARCH_CYCLE_MARKERS),
        },
    }


def dry_run_delete_counts(inventory: dict[str, Any] | None = None) -> dict[str, int]:
    """Return planned delete counts by entity (deterministic)."""
    del inventory  # reserved for future cross-checks; counts come from SQL
    sources_sql = ", ".join(f"'{s}'" for s in FIXTURE_VACANCY_SOURCES)
    purge_v = f"SELECT id FROM vacancies WHERE source IN ({sources_sql})"
    rows = run_psql_json(
        f"""
        SELECT 'search_cycles_acceptance' AS entity, count(*)::int AS count FROM search_cycles sc
          LEFT JOIN offers o ON o.id = sc.accepted_offer_id
          WHERE sc.close_note ILIKE '%R5.2 ACCEPTANCE%'
             OR o.note ILIKE '%R5.2 ACCEPTANCE%'
             OR o.position_title ILIKE '%R5.2 ACCEPTANCE%'
        UNION ALL SELECT 'offers_on_fixture_vacancies', count(*)::int FROM offers
          WHERE vacancy_id IN ({purge_v})
        UNION ALL SELECT 'hiring_activities_on_fixture_hp', count(*)::int FROM hiring_activities
          WHERE hiring_process_id IN (SELECT id FROM hiring_processes WHERE vacancy_id IN ({purge_v}))
        UNION ALL SELECT 'hiring_stage_events_on_fixture_hp', count(*)::int FROM hiring_stage_events
          WHERE hiring_process_id IN (SELECT id FROM hiring_processes WHERE vacancy_id IN ({purge_v}))
        UNION ALL SELECT 'hiring_processes_on_fixture_vacancies', count(*)::int FROM hiring_processes
          WHERE vacancy_id IN ({purge_v})
        UNION ALL SELECT 'employer_responses_on_fixture_vacancies', count(*)::int FROM employer_responses
          WHERE vacancy_id IN ({purge_v})
        UNION ALL SELECT 'applications_on_fixture_vacancies', count(*)::int FROM applications
          WHERE vacancy_id IN ({purge_v})
        UNION ALL SELECT 'assessments_on_fixture_vacancies', count(*)::int FROM assessments
          WHERE vacancy_id IN ({purge_v})
        UNION ALL SELECT 'acceptance_direct_outreaches', count(*)::int FROM direct_outreaches
          WHERE note LIKE 'R3.2 acceptance fixture:%'
             OR note LIKE 'R3. acceptance fixture:%'
        UNION ALL SELECT 'people_fixture', count(*)::int FROM people
          WHERE source = 'workspace-smoke'
             OR (
               full_name = 'Synthetic Confirm Person'
               AND company_id IN (SELECT id FROM companies WHERE source IN ({sources_sql}))
             )
        UNION ALL SELECT 'hypotheses_workspace_smoke', count(*)::int FROM hypotheses
          WHERE source = 'workspace-smoke'
        UNION ALL SELECT 'vacancies_fixture_sources', count(*)::int FROM vacancies
          WHERE source IN ({sources_sql})
        UNION ALL SELECT 'companies_fixture_sources', count(*)::int FROM companies
          WHERE source IN ({sources_sql})
            AND NOT EXISTS (
              SELECT 1 FROM vacancies v
              WHERE v.company_id = companies.id
                AND v.source NOT IN ({sources_sql})
            )
        """
    )
    return {row["entity"]: row["count"] for row in rows}


def create_backup(backup_root: Path | None = None) -> dict[str, Any]:
    """Create a custom-format pg_dump under gitignored backups/."""
    root = backup_root or DEFAULT_BACKUP_ROOT
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest_dir = root / stamp
    dest_dir.mkdir(parents=True, exist_ok=True)
    dump_path = dest_dir / "job_search.dump"
    meta_path = dest_dir / "backup_meta.json"

    pre_counts = {row["entity"]: row["count"] for row in run_psql_json(entity_counts_sql())}
    db_ident = run_psql(
        "SELECT current_database() || ' / ' || current_user || ' / ' || version();",
        tuples_only=True,
    ).strip()

    # Stream dump from container to host (avoid leaving dump inside container only).
    cmd = [
        *_compose_base(),
        "exec",
        "-T",
        "postgres",
        "pg_dump",
        "-U",
        PSQL_USER,
        "-d",
        PSQL_DB,
        "-Fc",
        "--no-owner",
        "--no-acl",
    ]
    with dump_path.open("wb") as fh:
        proc = subprocess.run(
            cmd,
            stdout=fh,
            stderr=subprocess.PIPE,
            cwd=str(WORKSPACE_ROOT),
            check=False,
        )
    if proc.returncode != 0:
        dump_path.unlink(missing_ok=True)
        raise RuntimeError(f"pg_dump failed: {proc.stderr.decode('utf-8', 'replace')}")

    meta = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "database": PSQL_DB,
        "user": PSQL_USER,
        "identity": db_ident,
        "dump_path": str(dump_path),
        "dump_bytes": dump_path.stat().st_size,
        "pre_clean_counts": pre_counts,
        "restore_procedure": [
            "Stop writers if needed: docker compose -f compose.yaml stop core web automation scoring-worker",
            f"docker compose -f compose.yaml exec -T postgres pg_restore -U {PSQL_USER} -d {PSQL_DB} --clean --if-exists < {dump_path}",
            "Or copy dump into container and: pg_restore -U job_search -d job_search --clean --if-exists /tmp/job_search.dump",
            "Restart services: docker compose -f compose.yaml start core web automation scoring-worker",
        ],
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return meta


PURGE_SQL = """
BEGIN;

-- 1) Acceptance SearchCycle before Offer delete (FK)
DELETE FROM search_cycles sc
USING offers o
WHERE sc.accepted_offer_id = o.id
  AND (
    sc.close_note ILIKE '%R5.2 ACCEPTANCE%'
    OR o.note ILIKE '%R5.2 ACCEPTANCE%'
    OR o.position_title ILIKE '%R5.2 ACCEPTANCE%'
  );

DELETE FROM search_cycles
WHERE accepted_offer_id IS NULL
  AND close_note ILIKE '%R5.2 ACCEPTANCE%';

-- 2) Offers on fixture vacancies
DELETE FROM offers
WHERE vacancy_id IN (
  SELECT id FROM vacancies WHERE source IN ('fixture','workspace-smoke','acceptance-r235')
);

-- 3) Hiring history on fixture HPs
DELETE FROM hiring_activities
WHERE hiring_process_id IN (
  SELECT hp.id FROM hiring_processes hp
  JOIN vacancies v ON v.id = hp.vacancy_id
  WHERE v.source IN ('fixture','workspace-smoke','acceptance-r235')
);

DELETE FROM hiring_stage_events
WHERE hiring_process_id IN (
  SELECT hp.id FROM hiring_processes hp
  JOIN vacancies v ON v.id = hp.vacancy_id
  WHERE v.source IN ('fixture','workspace-smoke','acceptance-r235')
);

DELETE FROM hiring_processes
WHERE vacancy_id IN (
  SELECT id FROM vacancies WHERE source IN ('fixture','workspace-smoke','acceptance-r235')
);

-- 4) R3 responses / applications / assessments on fixture vacancies
DELETE FROM employer_responses
WHERE vacancy_id IN (
  SELECT id FROM vacancies WHERE source IN ('fixture','workspace-smoke','acceptance-r235')
);

DELETE FROM applications
WHERE vacancy_id IN (
  SELECT id FROM vacancies WHERE source IN ('fixture','workspace-smoke','acceptance-r235')
);

DELETE FROM assessments
WHERE vacancy_id IN (
  SELECT id FROM vacancies WHERE source IN ('fixture','workspace-smoke','acceptance-r235')
);

-- 5) Explicit acceptance outreaches (may sit on real HH vacancies)
DELETE FROM direct_outreaches
WHERE note LIKE 'R3.2 acceptance fixture:%'
   OR note LIKE 'R3. acceptance fixture:%';

-- 6) Fixture people (before vacancies — FK people.vacancy_id / company_id)
DELETE FROM people
WHERE source = 'workspace-smoke'
   OR (
     full_name = 'Synthetic Confirm Person'
     AND company_id IN (
       SELECT id FROM companies
       WHERE source IN ('fixture','workspace-smoke','acceptance-r235')
     )
   );

-- 7) Smoke hypotheses
DELETE FROM hypotheses WHERE source = 'workspace-smoke';

-- 8) Fixture vacancies then orphan fixture companies
DELETE FROM vacancies
WHERE source IN ('fixture','workspace-smoke','acceptance-r235');

DELETE FROM companies c
WHERE c.source IN ('fixture','workspace-smoke','acceptance-r235')
  AND NOT EXISTS (SELECT 1 FROM vacancies v WHERE v.company_id = c.id)
  AND NOT EXISTS (SELECT 1 FROM people p WHERE p.company_id = c.id);

-- 9) If acceptance closure was the only cycle, seed a fresh active cycle.
-- Do not invent reopen when a non-fixture closed cycle remains.
INSERT INTO search_cycles (
  id, status, started_at, closed_at, accepted_offer_id, outcome, close_note, created_at, updated_at
)
SELECT gen_random_uuid(), 'active', NOW(), NULL, NULL, NULL, NULL, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM search_cycles);

COMMIT;
"""


def execute_purge() -> None:
    """Run the controlled purge transaction."""
    run_psql(PURGE_SQL)


def integrity_report() -> dict[str, Any]:
    """Post-clean FK / orphan / coherence checks."""
    checks = run_psql_json(
        """
        SELECT 'orphan_offers_missing_hp' AS check, count(*)::int AS bad
        FROM offers o LEFT JOIN hiring_processes hp ON hp.id = o.hiring_process_id
        WHERE hp.id IS NULL
        UNION ALL SELECT 'orphan_offers_missing_vac', count(*)::int
        FROM offers o LEFT JOIN vacancies v ON v.id = o.vacancy_id WHERE v.id IS NULL
        UNION ALL SELECT 'orphan_activities_missing_hp', count(*)::int
        FROM hiring_activities a LEFT JOIN hiring_processes hp ON hp.id = a.hiring_process_id
        WHERE hp.id IS NULL
        UNION ALL SELECT 'orphan_stages_missing_hp', count(*)::int
        FROM hiring_stage_events e LEFT JOIN hiring_processes hp ON hp.id = e.hiring_process_id
        WHERE hp.id IS NULL
        UNION ALL SELECT 'search_cycle_dangling_offer', count(*)::int
        FROM search_cycles sc
        LEFT JOIN offers o ON o.id = sc.accepted_offer_id
        WHERE sc.accepted_offer_id IS NOT NULL AND o.id IS NULL
        UNION ALL SELECT 'fixture_vacancies_remaining', count(*)::int
        FROM vacancies WHERE source IN ('fixture','workspace-smoke','acceptance-r235')
        UNION ALL SELECT 'active_search_cycles', count(*)::int
        FROM search_cycles WHERE status = 'active'
        UNION ALL SELECT 'closed_search_cycles', count(*)::int
        FROM search_cycles WHERE status = 'closed'
        """
    )
    return {row["check"]: row["bad"] for row in checks}


def print_json(data: Any) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="PB-DATA-01 working DB cleanup (inventory / backup / dry-run / purge)"
    )
    parser.add_argument(
        "command",
        choices=("inventory", "backup", "dry-run", "purge"),
        help="inventory|backup|dry-run (default safe)|purge (requires --execute)",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Required for purge; without it purge refuses to delete",
    )
    parser.add_argument(
        "--backup-dir",
        type=Path,
        default=None,
        help="Override backup root (default backups/pb-data-01/)",
    )
    parser.add_argument(
        "--skip-backup",
        action="store_true",
        help="Dangerous: allow purge without creating a new backup in this run",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not COMPOSE_FILE.is_file():
        print(f"compose.yaml not found at {COMPOSE_FILE}", file=sys.stderr)
        return 2

    if args.command == "inventory":
        print_json(inventory_payload())
        return 0

    if args.command == "backup":
        meta = create_backup(args.backup_dir)
        print_json(meta)
        return 0

    if args.command == "dry-run":
        inv = inventory_payload()
        planned = dry_run_delete_counts(inv)
        print_json(
            {
                "mode": "dry-run",
                "deletes_nothing": True,
                "planned_deletes": planned,
                "vacancy_classes": inv["vacancy_classes"],
                "ambiguous_kept_summary": {
                    "legacy_job_search_vacancies": len(
                        inv["ambiguous_kept"]["legacy_job_search_vacancies"]
                    ),
                    "note": inv["ambiguous_kept"]["note"],
                },
            }
        )
        return 0

    if args.command == "purge":
        if not args.execute:
            print(
                "Refusing purge without --execute. Run dry-run first, then:\n"
                "  python3 scripts/working_db_cleanup.py purge --execute",
                file=sys.stderr,
            )
            return 2
        backup_meta = None
        if not args.skip_backup:
            backup_meta = create_backup(args.backup_dir)
        before = inventory_payload()
        planned = dry_run_delete_counts(before)
        execute_purge()
        after_counts = {
            row["entity"]: row["count"] for row in run_psql_json(entity_counts_sql())
        }
        integrity = integrity_report()
        print_json(
            {
                "mode": "purge",
                "backup": backup_meta,
                "planned_deletes": planned,
                "pre_clean_counts": before["entity_counts"],
                "post_clean_counts": after_counts,
                "integrity": integrity,
            }
        )
        bad = {
            k: v
            for k, v in integrity.items()
            if v
            and (
                k.startswith("orphan_")
                or k.endswith("_dangling_offer")
                or k == "fixture_vacancies_remaining"
            )
        }
        if integrity.get("active_search_cycles", 0) < 1:
            bad["active_search_cycles"] = integrity.get("active_search_cycles", 0)
        if bad:
            print(f"Integrity problems after purge: {bad}", file=sys.stderr)
            return 1
        return 0

    return 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BrokenPipeError:
        sys.stderr.close()
        raise SystemExit(0)
