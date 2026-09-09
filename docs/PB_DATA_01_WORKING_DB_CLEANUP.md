# PB-DATA-01 — Working database cleanup

Maintenance command for removing **provable** test / synthetic / acceptance
fixture rows from the local working PostgreSQL database before Final Gate v1.

Does **not** reset the schema. Does **not** delete real HH / legacy migrated
history. Does **not** commit dumps (paths under `backups/` are gitignored).

## Commands

All commands run against the compose `postgres` service
(`compose.yaml`, database `job_search`).

```bash
# Inventory (read-only)
python3 scripts/working_db_cleanup.py inventory

# Restorable dump under backups/pb-data-01/<UTC-stamp>/
python3 scripts/working_db_cleanup.py backup

# Planned deletes (default safe mode; no DELETE)
python3 scripts/working_db_cleanup.py dry-run

# Backup + purge (requires --execute)
python3 scripts/working_db_cleanup.py purge --execute
```

Make wrappers:

```bash
make working-db-inventory
make working-db-dry-run
make working-db-backup
make working-db-purge   # still requires CONFIRM=1
```

## Classification

| Class | Criterion | Action |
|---|---|---|
| **A real** | Vacancy/Company `source` ∈ `{hh, legacy_job_search}` | KEEP |
| **B fixture** | `source` ∈ `{fixture, workspace-smoke, acceptance-r235}` + dependents | DELETE |
| **C ambiguous** | Anything else / business-content-only guess | KEEP + report |

Extra B rows (without deleting the parent real Vacancy):

- `DirectOutreach.note` starting with `R3.2 acceptance fixture:`
- `People` with `source=workspace-smoke`, or `full_name='Synthetic Confirm Person'` tied to a fixture company
- `Hypotheses` with `source=workspace-smoke`
- `SearchCycle` / accepted Offer text containing `R5.2 ACCEPTANCE`

## Restore

See `backup_meta.json` next to the dump. Typical flow:

```bash
docker compose -f compose.yaml stop core web automation scoring-worker
docker compose -f compose.yaml exec -T postgres \
  pg_restore -U job_search -d job_search --clean --if-exists \
  < backups/pb-data-01/<stamp>/job_search.dump
docker compose -f compose.yaml start core web automation scoring-worker
```

## After purge

- Fixture closed `SearchCycle` is removed; if no cycle remains, one **active**
  cycle is inserted (maintenance repair — not a product reopen feature).
- Automation is left **disabled** but manually enable-able (enable/run-now no
  longer blocked by fixture closure). Acquisition is **not** auto-started.
