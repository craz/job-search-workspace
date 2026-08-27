# R2.2.3 — Vacancy ingest / content_hash evidence

**Date:** 2026-08-27  
**Status:** READY FOR OWNER ACCEPTANCE (local; not pushed)

## API

`POST /api/v1/vacancies/ingest` → `{outcome, vacancy}`  
Outcomes: `created` | `updated` | `unchanged`  
No `Idempotency-Key`. Core owns `content_hash`.

## Live bounded evidence (Core :18000)

| Step | Result |
|---|---|
| A first ingest | `created`, UUID `067e1a45-…`, status `new`, hash set |
| B identical repeat | `unchanged`, same UUID, hash unchanged |
| User status → reviewing | status `reviewing`, hash unchanged |
| C description change | `updated`, same UUID, status still `reviewing`, hash changed |
| D repeat changed | `unchanged`, same UUID |
| Identity | single row for `(hh, 136706048)` |

Gates: Core unit 45 · integration 27 · contract 9 · bdd 18; HH unit 113+1skip · contract 13 · bdd 13.

Migration head: **`20260827_11`** (unchanged; company identity fix is mapper/semantics only).

## Company identity (owner remark)

- Stable employer id → `Company(hh, <employer_id>)`, shared across vacancies.
- No employer id → `Company(hh, vacancy:<vacancy_external_id>:employer)` —
  same display name on different vacancies never merges.
