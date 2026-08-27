# R2.2.A — Integrated acceptance (R2.2.1–R2.2.5)

**Date:** 2026-08-28 (UTC+3)  
**Status:** READY FOR OWNER ACCEPTANCE (local evidence, not pushed)  
**Migration head:** `20260828_13`

## Accepted baseline (pushed)

| Repo | SHA | Notes |
|---|---|---|
| Core | `1da3c57` | temporal provenance |
| HH | `fdf6773` | resume_suitable + egress guard |
| Web | `0f00a44` | primary UX + recovery UI |
| workspace | `07da8f8` | R2.2.5 complete |

**R2.2.5 = COMPLETE · OWNER ACCEPTED · PUSHED**

---

## 1. Canonical runtime (`make up`)

| Check | Result |
|---|---|
| Core healthy | yes (`/health/ready` 200) |
| HH healthy | yes |
| Web up | yes (`127.0.0.1:18080`) |
| hh-egress | running |
| migration head | `20260828_13` (single head) |
| HH `/health/ready` | `status=ok`, `egress.proxy_url=http://hh-egress:3128`, `proxy_reachable=true` |
| HH resumes | `status=available`, `code=ready` |

Startup contract: `make up` → `host_http_proxy_socket.py ensure` + `docker-compose.hh-egress.yml` override.

---

## 2. Active resume / provenance

| Field | Value |
|---|---|
| HH active external_id | `f3e5e5f7ff0f50d3e50039ed1f4436664d7338` |
| HH active title | Project Manager / Руководитель IT-проектов |
| Core `hh_resume_link` | same external_id, `status=active` |
| CandidateProfile | `e96cb6cc-7594-4c65-855b-a86770db434a` |
| ProfileVersion | `4fa80565-0d36-4290-827d-f482546aa3f7` (`r1-default`) |
| ResumeVersion | `c39fa10d-1ba2-4bd7-978d-4256987163d4` (`content_state=synced`) |

Search uses active HH resume identity (not hardcoded in orchestration).

---

## 3. Primary live Web flow

**URL:** http://127.0.0.1:18080/#vacancies  
**Action:** `POST /api/v1/hh/vacancies/suitable` (same as «Проверить подходящие»)

| Step | Evidence |
|---|---|
| Web → HH suitable | `code=ready` |
| active resume SERP | `acquisition_kind=resume_suitable` |
| SERP guard | `serp_guard.ok=true`, `source_total=2270` |
| ordering | `execution_snapshot.order=publication_time` |
| bounded pages | `max_pages=1`, no fake `page_size` |
| detail + ingest | 50 items, `outcome=unchanged` (existing DB) |
| SearchRun finalize | `status=success` |
| Vacancy list | 521 rows, `first_seen_at DESC` |

**Primary SearchRun id:** `8067198e-a7b8-4b9f-ac27-241541308328`

### SearchRun model (Core API)

```json
{
  "acquisition_kind": "resume_suitable",
  "search_profile_id": null,
  "criteria_snapshot": {},
  "candidate_context_snapshot": {
    "hh_resume_external_id": "f3e5e5f7ff0f50d3e50039ed1f4436664d7338",
    "hh_resume_title": "Project Manager / Руководитель IT-проектов",
    "profile_version_id": "4fa80565-0d36-4290-827d-f482546aa3f7",
    "resume_version_id": "c39fa10d-1ba2-4bd7-978d-4256987163d4"
  },
  "execution_snapshot": {
    "transport": "browser",
    "order": "publication_time",
    "max_pages": 1,
    "discovery": "resume_suitable"
  },
  "source_total": 2270,
  "found_count": 50,
  "created_count": 0,
  "updated_count": 0,
  "unchanged_count": 50,
  "error_count": 0,
  "status": "success"
}
```

`started_at` / `finished_at` present on persisted run.

---

## 4. source_total vs processed

| Metric | Value | Meaning |
|---|---|---|
| `source_total` | 2270 | HH suitable SERP total |
| `found_count` / processed | 50 | bounded page actually processed |
| Web copy | `HH предлагает: 2 270` · `Проверено: 50. Новых: 0. Обновлено: 0. Уже в базе: 50.` | `app.js` `renderSuitableSummary` |

Counters match persisted SearchRunItems: `total=50`, sum(outcomes)=50.

---

## 5. Canonical Vacancy / dedupe

Sample live HH vacancy (`external_id=134674373`):

| Field | Present |
|---|---|
| UUID | `b12a42c5-4f50-477c-b173-a355e3161f5d` |
| source | `hh` |
| title, url, description | yes (full description) |
| company.name | yes |

- Duplicate `(source, external_id)` pairs in list: **0**
- Repeat run: **50/50** vacancy UUIDs preserved for same external_ids

Company identity (unit tests green):

- `test_stable_employer_id_reused_across_vacancies`
- `test_same_name_without_employer_id_isolates_companies`
- `test_vacancy_detail_falls_back_to_vacancy_scoped_company_identity`

---

## 6. Temporal provenance

| Vacancy | first_seen_at | last_seen_at (after repeat) | Rank |
|---|---|---|---|
| Руководитель проектов (ИТ) | `2026-08-27T22:57:30` | `2026-08-27T23:25:21` | 0 |
| Product Manager | `2026-08-27T20:44:14` | `2026-08-27T23:25:21` | 1 |

- `first_seen_at` preserved on repeat unchanged ingest
- `last_seen_at` advanced on repeat
- Older `first_seen_at` does not jump above newer-first-seen rows
- `source_published_at` may be null (accepted)

Unit: `tests/unit/test_vacancy_temporal.py` (green).

---

## 7. Repeat run

**Repeat SearchRun id:** `3d5d0944-63b3-492b-b65d-824852afb13e`

| Check | Result |
|---|---|
| New SearchRun id | yes |
| Same resume provenance | yes |
| outcomes | 50× `unchanged` |
| duplicate Vacancy rows | none |
| terminal status | `success` (max_pages boundary = success, not partial) |

---

## 8. profile_search regression (API/tests)

| Rule | Test |
|---|---|
| `resume_suitable` forbids `search_profile_id` | `core/tests/unit/test_search_runs.py::test_resume_suitable_requires_null_profile_and_resume_context` |
| `profile_search` requires `search_profile_id` | `core/tests/unit/test_search_runs.py::test_profile_search_still_requires_search_profile` |
| HH orchestration unchanged | `hh/tests/unit/test_search_run_orchestration.py` (profile_search paths) |

PB-FUTURE-05 (manual SearchProfile Web staging) remains deferred.

---

## 9. Recovery matrix (A–J)

| Case | Evidence |
|---|---|
| **A** local egress broken | `hh/tests/unit/test_egress.py`, `test_resumes.py` proxy cases; `web/tests/contract/test_hh_egress_recovery.py`; `/health/ready` egress block |
| **B** login/not authorized | `hh/tests/unit/test_resumes.py::test_without_browser_login_skips_reader` |
| **C** CAPTCHA/action_required | `test_captcha_page_is_action_required` |
| **D** profile_locked | `test_profile_locked_offers_confirm` |
| **E** resume suitable page mismatch | `hh/tests/unit/test_resume_suitable.py::test_validate_resume_suitable_page_*` |
| **F** first page failure → failed | `test_search_run_orchestration.py::test_first_page_failure_failed` |
| **G** page failure after work → partial | `test_page_failure_after_first_page_partial_no_fake_items` |
| **H** detail failure → partial, others continue | `test_detail_failure_continues_partial`, `test_ingest_failure_continues_partial` |
| **I** zero results → success | `test_zero_result_success` |
| **J** terminal immutability | `core/tests/integration/test_search_runs_api.py`, `test_terminal_run_rejects_items_and_re_finalize` |

---

## 10. Test gates (accepted baseline)

| Repo | unit | integration | contract | bdd |
|---|---:|---:|---:|---:|
| Core | 55 | 27 | 9 | 18 |
| HH | 140 (+1 skip) | — | 16 | 13 |
| Web | 5 | 36 | 11 | 10 |
| workspace | 30 | — | — | — |

All green on accepted SHAs before push and after `make up`.

---

## 11. Product code changes in R2.2.A

**None.** Verification/evidence only.

---

## 12. Known non-blocking debt

- stale-running SearchRun reclaim (pre-existing)
- PB-FUTURE-05: manual SearchProfile Web staging deferred
- OSINT `website_url` discovery (R3)
- scoring / Ollama (R2.4+)

---

## Owner checklist

1. `make up` → all services healthy, egress ok.
2. Active resume visible in Web strip.
3. «Проверить подходящие» → summary with `HH предлагает` vs `Проверено`.
4. Vacancy list: year in «Получена», newest `first_seen_at` first.
5. Repeat run: unchanged, no duplicates, `last_seen_at` moves.
6. Misconfigured proxy shows local egress message (not HH outage).
