# R2.2 — SearchProfile + HH vacancy ingestion / normalization / dedupe

**Status:** **READY FOR OWNER ACCEPTANCE** (docs-only; owner remark corrections applied)  
**Production implementation:** **NOT STARTED**  
**R2.1:** **COMPLETE · OWNER ACCEPTED · PUSHED**  
**R2.3:** **NOT STARTED**

**Canonical SoT:** Google Drive **Job Search** (Product Backlog, Roadmap, R2).  
**Evidence / decision date:** 2026-08-27 (owner remark same day).

This document is the accepted-shape decomposition for R2.2 after owner review
and model-boundary corrections. It does **not** authorize production code,
migrations, or API changes until **OWNER ACCEPTED**.

---

## 0. Status

```text
R2.1 = COMPLETE · OWNER ACCEPTED · PUSHED
R2.2 decomposition = READY FOR OWNER ACCEPTANCE
R2.2 production = NOT STARTED
R2.3 = NOT STARTED
```

---

## 1. Product goal

```text
minimal SearchProfile (intent/criteria)
  → SearchRun (criteria_snapshot + execution_snapshot)
  → HH discovery (list-first; detail when needed for scoring-ready content)
  → normalize + content_hash
  → Core upsert (source + external_id)
  → SearchRunItem per Vacancy (created|updated|unchanged|error)
  → aggregate run summary + «Вакансии» UX
```

**R2.2 does not score.** Scoring = **R2.3**, but R2.2 Vacancy source content must
be sufficient for later scoring.

Mapped PBIs: **PB-02** + minimal **PB-01 SearchProfile**.  
**Not** PB-FUTURE-01.

---

## 2. Owner decisions (locked)

Preserved unchanged:

- persisted mutable minimal SearchProfile; not resume-derived
- SearchRun immutable snapshots
- identity = `(source, external_id)`; HH `source=hh`
- source-owned `content_hash`; created/updated/unchanged = ingestion outcomes
- `Vacancy.status` = user workflow only
- same identity + changed content → update, not new Vacancy
- UUID / relations / user state preserved
- missing from run ≠ archived; archived/closed only by explicit HH signal
- no fuzzy/LLM cross-id dedupe
- no silent browser vacancy search
- slices **R2.2.1 → R2.2.2 → R2.2.3 → R2.2.4 → R2.2.5 → R2.2.A**

### 2.1 SearchProfile vs execution policy (owner remark)

**SearchProfile** = user search **intent / criteria** only.

Allowed: semantic HH filters (`text`, `area`, `salary`, `experience`,
`employment`, `schedule`, `search_field`, `only_with_salary`, and other
**real** HH search criteria when confirmed).

**Not** in SearchProfile:

- `page_size`, `max_pages`
- `order` / ordering strategy
- retry / runtime / transport controls

Those belong to **execution / acquisition policy**, snapshotted on the run.

**SearchProfileVersion** still not required.

### 2.2 SearchRun ↔ Vacancy provenance (owner remark)

Aggregate counters alone are insufficient. Persist **SearchRunItem**
(alias: SearchRunVacancy) linking each discovered Vacancy to the run.

One Vacancy may appear in many SearchRuns.

### 2.3 SearchRun lifecycle (owner remark)

Statuses: **`running` | `success` | `partial` | `failed`**.

- `started_at` at start
- `finished_at` only in a **terminal** state
- unfinished run must never look like `success`

### 2.4 List vs detail (owner decision — closed)

**DISCOVERY = LIST-FIRST.**

If list payload lacks full content needed for R2.3 Scoring (especially full
`description` and other scoring-relevant source fields), R2.2 **must** perform
vacancy **detail fetch**. Correctness over premature “skip refetch known”
optimization.

R2.2.2 capability proof must establish: list fields, detail fields, detail
endpoint availability, API/auth/proxy, pagination, 403 cause, rate limits.

Browser fallback still **forbidden** without separate OWNER DECISION.

---

## 3. Final SearchProfile fields

Mutable, minimal, single-user MVP:

```text
SearchProfile
  - id
  - label?: str
  - text: str                              # required MVP query
  - area_id?: str
  - salary?: { from?, to?, currency? }
  - experience?: HH dictionary id
  - employment?: HH dictionary id
  - schedule?: HH dictionary id
  - search_field?: name | company_name | description
  - only_with_salary?: bool
  - (+ other confirmed HH semantic criteria only)
  - created_at / updated_at
```

**Excluded:** `page_size`, `max_pages`, `order`, transport/retry knobs.

Non-goals: SearchProfileVersion; studio UI; resume-derived builder.

---

## 4. Final execution policy fields

Not stored as SearchProfile product criteria. Concrete values for a run are
frozen in SearchRun `execution_snapshot`.

```text
Execution policy (runtime / acquisition)
  - order / ordering strategy          # e.g. publication_time
  - page_size
  - max_pages
  - (+ other needed acquisition knobs: timeouts, retry budget, detail-fetch flag defaults)
```

Product defaults may live in config/code or a non-SearchProfile settings object;
exact persistence of *defaults* is an implementation detail. What matters for
provenance: **each SearchRun records the execution settings actually used**.

---

## 5. SearchRun final model / lifecycle

```text
SearchRun
  - id
  - search_profile_id
  - source = "hh"
  - criteria_snapshot: JSON      # immutable SearchProfile semantic criteria
  - execution_snapshot: JSON     # immutable order/page_size/max_pages/...
  - candidate_context_snapshot?: JSON  # optional ids only; never derives criteria
  - status: running | success | partial | failed
  - started_at                   # set when run starts
  - finished_at?                 # set only when terminal
  - found_count                  # denormalized summary
  - created_count
  - updated_count
  - unchanged_count
  - error_count
  - pagination / progress metadata as needed
  - error_code / recovery_hint?: optional
```

| Status | Meaning |
|---|---|
| `running` | In progress; `finished_at` null |
| `success` | Terminal; pagination completed as planned; no blocking failure |
| `partial` | Terminal; some pages ingested but pagination/run incomplete |
| `failed` | Terminal; could not complete meaningfully / hard failure |

Successful pages may ingest while `running`; terminal status must be honest.

---

## 6. SearchRun ↔ Vacancy association

Working name: **`SearchRunItem`** (acceptable alias: SearchRunVacancy).

```text
SearchRunItem
  - id
  - search_run_id
  - vacancy_id                 # Core Vacancy UUID (when known)
  - outcome: created | updated | unchanged | error
  - discovered_at?: datetime
  - page?: int
  - source_external_id?: str   # HH id; useful especially on error before Vacancy exists
  - error_code / error_detail?: optional
```

Rules:

- Do **not** dump full Vacancy payload into the item.
- After a run finishes, the set of items answers “which vacancies this run saw”
  and “what ingestion outcome each had”.
- SearchRun aggregate counts remain a denormalized summary of items.
- Unique recommendation (implementation): `(search_run_id, source_external_id)`
  or `(search_run_id, vacancy_id)` once linked — avoid duplicate item rows per run.

---

## 7. Final list / detail rule

1. Discover vacancies via **search list** (paginated).
2. If list fields are insufficient for scoring-ready local Vacancy content
   (notably full description / other scoring-relevant source fields) → **detail
   fetch** before treating the vacancy as fully ingested for R2.2.
3. `content_hash` covers the normalized source content actually stored (list +
   detail as required).
4. Do not skip detail for “already known” vacancies as a first optimization;
   correctness first.
5. Capability proof in **R2.2.2** documents exact list vs detail field sets and
   whether detail endpoint is available under the same transport constraints.

---

## 8. Vacancy upsert (unchanged essence)

- Identity `(source, external_id)`.
- Prefer dedicated upsert/ingest contract; keep manual create intact.
- Same hash → `unchanged`; different hash → update source-owned fields → `updated`.
- Preserve UUID, relations, `Vacancy.status`.
- Missing from run → no auto archive/delete.
- Explicit HH archived/closed signal → source-state only; not funnel status.

---

## 9. Conflicts resolved (incl. owner remark)

| Topic | Resolution |
|---|---|
| page_size/order in SearchProfile | **Moved** to execution policy / `execution_snapshot` |
| Run provenance | **SearchRunItem** required |
| Incomplete run as success | **Forbidden**; use `running` / `partial` / `failed` |
| List vs detail | **List-first discovery**; detail when content insufficient for scoring |
| HH API “works” | Scaffold only; live **403** until capability proof |
| Browser fallback | Still separate OWNER DECISION only |

---

## 10. Product US / TECH-US / EXT

### US-02.1 — Minimal SearchProfile (criteria only)

**AC:** persists semantic filters; no execution knobs; not resume-derived.  
**Repos:** Core (+ Web).

### US-02.2 — SearchRun + SearchRunItem provenance

**AC:** `running`→terminal lifecycle; `criteria_snapshot` + `execution_snapshot`;
per-vacancy items with outcomes; aggregates match items.  
**Repos:** Core + HH orchestration.

### US-02.3 — Source-identity upsert (+ detail when needed)

**AC:** created/updated/unchanged; scoring-relevant source content stored when
transport allows; UUID/relations/status preserved.  
**Repos:** Core + HH.

### US-02.4 — Vacancies Web flow

**AC:** profile summary; find/update; last run status/counts; HH vacancies visible;
no scoring UI.  
**Repos:** Web.

### TECH-US-02.T1 — HH acquisition + capability proof

List/detail fields, endpoints, auth/proxy, pagination, 403 cause, rate limits;
no silent browser.  
**Repos:** HH.

### TECH-US-02.T2 — Normalize + content_hash

Allowlist; hash over source-owned stored fields.  
**Repos:** HH + Core.

### EXT-02.E1 — Semantic / cross-id dedupe — deferred  
### EXT-02.E2 — HH saved searches — deferred  
### EXT-02.E3 — Browser RO vacancy search — deferred (owner decision)  
### DEBT-02.D1 — Scaffold “sync implemented” wording — when implementation starts

---

## 11. Updated internal slices

| Slice | Acceptance meaning |
|---|---|
| **R2.2.1** | Persisted **SearchProfile** (criteria-only) + **SearchRun** (+ lifecycle) + **SearchRunItem** model/API; no live HH required |
| **R2.2.2** | HH acquisition capability proof + list/detail/pagination transport; browser only after separate owner decision if API unavailable |
| **R2.2.3** | Normalize + detail-when-needed + Vacancy upsert + `content_hash` → created/updated/unchanged |
| **R2.2.4** | End-to-end SearchRun: profile → execution → HH pages → upsert → SearchRunItems → summary/recovery |
| **R2.2.5** | Human-readable Web flow on **«Вакансии»** |
| **R2.2.A** | Integrated R2.2 acceptance |

Difference vs prior wording: R2.2.1 now explicitly includes **SearchRunItem** and
criteria/execution snapshot split; R2.2.2/R2.2.3 encode **list-first + detail
when needed**.

---

## 12. Acceptance target

> По SearchProfile (intent) Job Search запускает SearchRun с зафиксированными
> criteria + execution settings, list-first находит HH vacancies, при
> необходимости добирает detail для scoring-ready content, upsert’ит по
> `(source, external_id)`, пишет SearchRunItem outcomes и показывает результат
> в «Вакансии» без copy-paste.

---

## 13. Repo impact (later)

| Repo | Work |
|---|---|
| Core | SearchProfile, SearchRun, SearchRunItem, vacancy upsert + content_hash |
| HH | capability proof, list+detail acquisition, normalize, orchestration |
| Web | profile (criteria) UX, run CTA, last-run summary |
| Scoring | unchanged in R2.2 |

---

## 14. Remaining open owner decisions

1. **After capability verification:** if official vacancy API remains
   403/unavailable — allow **browser RO vacancy search**?
   (Default until answer: **no**.)

List-vs-detail is **closed** (list-first + detail when needed for scoring content).

---

## 15. Non-scope (hard)

- Scoring / Ollama / embeddings / SCORING_SERVICE_FOUNDATION
- PB-04 decisions / apply / OSINT / outreach
- other providers / PB-FUTURE-01
- silent browser vacancy fallback
- SearchProfileVersion / full SearchProfile redesign
- fuzzy cross-id dedupe
- storing execution knobs inside SearchProfile

---

## 16. Final framing

```text
R2.1 = COMPLETE · OWNER ACCEPTED · PUSHED

R2.2 DECOMPOSITION = READY FOR OWNER ACCEPTANCE

R2.2 production implementation = NOT STARTED

R2.3 = NOT STARTED
```
