# R2.2.4 — SearchRun orchestration evidence

**Date:** 2026-08-27  
**Status:** READY FOR OWNER ACCEPTANCE (local; **not** pushed)

## Architecture

```text
POST /api/v1/vacancies/search  (HH)
  → run_vacancy_search
      → Core get SearchProfile
      → Core start SearchRun (criteria_snapshot + execution_snapshot)
      → browser acquire_vacancies (immutable snapshots only)
      → vacancy_detail_to_ingest → Core /vacancies/ingest
      → Core SearchRunItem per unique source_external_id
      → Core finalize (counters from items)
```

## Live first run

| Field | Value |
|---|---|
| SearchProfile | `c4e2f98b-…` text=`python` area_id=`1` |
| SearchRun | `8a32f3cc-…` status=`success` |
| criteria_snapshot | text=python, area_id=1 |
| execution_snapshot | order=publication_time, max_pages=1, transport=browser (**no page_size**) |
| Browser | found_text «Найдено 3 686…», observed_page_size=50, max_pages_reached=true |
| Items | 50 unique external ids |
| Counters | found=50, created=49, updated=1, unchanged=0, error=0 |
| Detail | sample vacancy `136706609` description_len=2990 |
| Vacancy rows | 50 tracked ids, **0 duplicates** |

## Live repeat run

| Field | Value |
|---|---|
| SearchRun | `984ae0bb-…` (**new** id) |
| Counters | found=50, created=0, updated=0, unchanged=50, error=0 |
| UUID stability | 50/50 common ids kept same vacancy_id |

## Failure-path evidence (deterministic unit)

`tests/unit/test_search_run_orchestration.py`:

- A detail failure → partial, other items continue  
- B page failure after page 1 → partial, no synthetic items  
- C first-page failure → failed  
- D zero result → success, zero counters  
- E action_required / CAPTCHA before work → failed + recovery  
- F repeat → new run, unchanged outcomes  
- immutable snapshot mid-run; dedupe within run; terminal immutability  

## Gates

- Core: unit 48 · integration 27 · contract 9 · bdd 18  
- HH: unit 128+1skip · contract 16 · bdd 13  
- migration head: **`20260827_11`**

## Non-scope confirmed

R2.2.5 Web **NOT STARTED**. R2.3 **NOT STARTED**. No R2.2.4 push.
