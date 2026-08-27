# R2.2 — Search context + HH vacancy ingestion / normalization / dedupe

**Status:** **READY FOR OWNER REVIEW** (analysis + decomposition only)  
**Production implementation:** **NOT STARTED**  
**R2.1:** **COMPLETE · OWNER ACCEPTED · PUSHED**  
**R2.3:** **NOT STARTED**

**Canonical SoT:** Google Drive **Job Search** (Product Backlog, Roadmap, R2).  
**Evidence date:** 2026-08-27.

This document proposes R2.2 product/tech decomposition. It does **not**
authorize production code, migrations, or API changes.

---

## 1. Product goal

After R2.1 the product already has:

```text
active HH account/session
  + active HH resume
  + local immutable ResumeVersion
```

R2.2 removes manual copy-paste of vacancies:

```text
search context
  → HeadHunter vacancy discovery
  → read / normalize
  → Core import
  → dedupe / update
  → понятный набор new / known / updated
```

**R2.2 does not score vacancies.** Scoring starts in **R2.3**.

Mapped PBIs: primarily **PB-02**; search-context slice of **PB-01** only as far
as needed for filters (not full SearchProfile productization). Explicitly
**not** PB-FUTURE-01 (resume-derived HH search).

---

## 2. Conflicts / SoT notes

| Topic | Google Doc | Repo | Resolution for this review |
|---|---|---|---|
| R2.1.A docs push | R2 tab (as of read): evidence `5df713c` **не PUSHED** | Workspace `5df713c` **pushed** to `origin/main` after OWNER ACCEPT | **Repo/runtime newer** — update Google Doc R2 status when convenient |
| PB-02 coverage | «HH пока не выполняет реальное чтение» / live ingestion gap | Scaffold `vacancies sync` + normalize + Core idempotent create; live `GET /vacancies` **403** today | **Aligned on gap**: scaffold ≠ product flow |
| ARCHITECTURE / HH README | «vacancy sync implemented» | True as **bootstrap CLI/path**, not live product acceptance | Treat as **ADAPT**, not COMPLETE R2.2 |
| SearchProfile | PB-01 still open for full SearchProfile | No SearchProfile model/code; R2.1 deferred it | See open decisions §19 |

No silent choice where Google Doc and repo conflict on product meaning.

---

## 3. Two contexts (do not mix)

### A. Candidate / resume context (exists)

- `CandidateProfile` / `ProfileVersion` (`r1-default`)
- active HH resume link
- immutable `ResumeVersion` (R2.1)

Used later by Scoring (R2.3). **Not** the vacancy query.

### B. Vacancy search context (R2.2 needs)

Parameters that drive HH discovery:

- query / roles text
- location / area
- salary bounds
- employment / schedule / experience (HH dictionary ids)
- search fields (`name` / `company_name` / `description`)
- order / freshness window
- pagination cursors / page budget
- last successful / failed sync run metadata

**Recommendation:** introduce a bounded **`VacancySearchContext`** (name TBD by
owner) separate from Candidate/Resume entities. Do **not** invent a full
SearchProfile UI/lifecycle in R2.2 unless owner explicitly wants that name/entity
as the R2.2 MVP carrier.

---

## 4. Existing reusable implementation

| Area | Status | Verdict |
|---|---|---|
| Core `Vacancy` + `Company` `(source, external_id)` unique | Implemented | **REUSE** identity |
| Core `POST /api/v1/vacancies` + `Idempotency-Key` | Create/replay only; **no update** of changed payload | **ADAPT** (need upsert/update semantics) |
| Vacancy funnel `status` (`new/reviewing/shortlisted/rejected`) | User/funnel state | **REUSE**; do not overload with HH archived |
| HH `HttpHhApi.search(text, per_page)` | One page, `text` only | **ADAPT** (filters, pages, error taxonomy) |
| HH `normalize_vacancy` | title/url/employer/description-or-snippet | **ADAPT** (richer fields when available) |
| HH `sync_vacancies` | fetch → create loop; counts synced≈attempts | **ADAPT** (new/known/updated/errors; resume after partial) |
| CLI `vacancies sync --text` | Exists | **ADAPT** into product sync |
| Web Vacancies list + manual add dialog | List/status/OSINT/assessment display | **REUSE** list; **NEW** sync UX strip |
| Historical vacancies (`hh`, `legacy_job_search`, smoke) | ~419 in live DB | **REUSE** as known corpus; migration tooling **IGNORE AS LEGACY** |
| Browser RO (resumes) | Proven for EXTERNAL_BLOCKED API cases | **Candidate fallback** only if API remains blocked — not auto-expand |
| Scoring / Assessments | Present but out of R2.2 | **IGNORE** for this stage |

---

## 5. Exact HH vacancy-search capabilities (live probes 2026-08-27)

Transport path: Compose `hh` → `hh-egress` proxy (same path as R1).

| Endpoint | Result |
|---|---|
| `GET /me` (Bearer) | **200** (`auth_type=applicant`) |
| `GET /dictionaries` | **200** (search field/order/employment/schedule/experience dictionaries present) |
| `GET /areas` | **200** |
| `GET /vacancies?...` public | **403** `forbidden` |
| `GET /vacancies?...` Bearer | **403** `forbidden` |
| `GET /vacancies/{id}` | **403** `forbidden` |
| `GET /negotiations` | **403** `forbidden` (known EXTERNAL_BLOCKED) |
| Host direct `api.hh.ru` | timeout (egress required) |

**Implication:** official vacancy search API is the preferred design target and
already coded as a scaffold, but **current live environment cannot read
vacancies via API**. This mirrors R1 `/resumes/mine` EXTERNAL_BLOCKED pattern.

Dictionary-backed filters (conceptually supported by HH):

- `vacancy_search_fields`: name / company_name / description
- order: publication_time, salary_*, relevance, distance
- employment / schedule / experience ids
- text query + pagination (`page`, `per_page`, `found`, `pages` — when API allows)

Saved-searches API: not proven live (blocked before useful probe). Do not assume.

**Detail fetch:** when search works, list items are partial; full `description` /
`key_skills` typically need `GET /vacancies/{id}` (currently also 403).

---

## 6. Proposed minimal search-context model

MVP fields (persisted, operator-editable):

```text
VacancySearchContext
  - id / label (single active context for single-user MVP is enough)
  - text: str                 # HH text query
  - area_id: optional
  - salary: optional {from, to, currency}
  - experience: optional HH id
  - employment / schedule: optional HH ids
  - search_field: optional (name|company_name|description|default)
  - order_by: optional (default publication_time)
  - only_with_salary: optional bool
  - page_size / max_pages: int bounds
  - created_at / updated_at
```

Sync run report (append-only or last+history lite):

```text
VacancySyncRun
  - search_context_id
  - started_at / finished_at
  - status: success | partial | failed
  - fetched / created / unchanged / updated / errors
  - last_page_completed
  - error_code / recovery hint
```

**Not in MVP:** multi-profile SearchProfile studio, resume-derived query builder
(PB-FUTURE-01), multi-provider contexts.

---

## 7. Current Core Vacancy model

Exact columns (`services/core/.../models.py`):

- identity: `id`, `source`, `external_id` — **UNIQUE (`source`,`external_id`)**
- `company_id` → `Company` (`source`,`external_id` unique)
- `title`, `url`, `description` (nullable)
- funnel `status`: `new | reviewing | rejected | shortlisted`
- write meta: `idempotency_key` **UNIQUE**, `request_fingerprint`
- `created_at`, `updated_at`
- relations: `applications`, `people`, `assessments`

HTTP create body today: `company_name`, `company_external_id`, `source`,
`external_id`, `title`, `url`, `description?`.

**Gaps vs R2.2 needs:** no salary/location/employment/work-format/published_at/
HH archived flag/raw metadata; **no update path** for changed content (same
idempotency key + changed fingerprint → conflict; different key + same
source/external_id → `VacancyAlreadyExistsError`).

---

## 8. Proposed normalized Vacancy contract (R2.2 target)

Keep identity:

- `source = "hh"`
- `external_id` = HH vacancy id
- `url` = `alternate_url` (canonical public URL)

Normalize when present in source (do not invent):

| Field | Source |
|---|---|
| title | `name` |
| employer/company | `employer.id` + `employer.name` |
| description | detail `description` or search `snippet` until detail available |
| salary | `salary` / `salary_range` structured JSON if present |
| location | `area` (+ address if useful) |
| employment / schedule / experience | HH dictionary objects → ids + names |
| work_format | if present |
| published_at / created_at | HH timestamps |
| hh_archived / closed | HH flags when present |
| raw_metadata | small allowlisted JSON for provenance (ids, hashes) — not full dump |

Storage shape (implementation choice later): either typed columns + JSONB
`attributes`, or JSONB envelope with schema_version. **Owner decision** if Core
schema expansion is allowed in R2.2.1 vs phased.

---

## 9. Identity / dedupe strategy

### 1) Same HH vacancy reread (MVP mandatory)

Key: `(source=hh, external_id)`.

Repeated ingestion **must not** create a second Core Vacancy.

### 2) Semantic duplicates (different HH ids / mirrors)

**Out of R2.2 MVP.** No fuzzy/LLM dedupe. Optional later EXT.

Cross-source (`legacy_job_search` vs `hh`) merge: **not** automatic in R2.2;
historical rows stay as known local vacancies.

---

## 10. Update semantics (proposal)

When same `(source, external_id)` is seen again:

| Observation | Behavior |
|---|---|
| Payload fingerprint unchanged | `unchanged`; bump last_seen; no funnel status change |
| Material fields changed (title/desc/salary/…) | **update in place** current Vacancy row; preserve `id`; preserve funnel `status` and Assessment/Application links |
| HH marks archived/closed | set HH lifecycle flag / local `source_state`; **do not** auto-set funnel `rejected` |
| Disappears from search page set | mark `missing_from_last_search` / last_seen stale — **do not delete** |

Do **not** introduce full event sourcing in R2.2. Optional lite:
`content_fingerprint` + `last_synced_at` is enough. Important change history for
scoring can wait unless owner demands it.

---

## 11. Behaviour matrix A–J

| | Scenario | Expected |
|---|---|---|
| A | First search run | Fetch pages → create vacancies → report created counts; run=success/partial |
| B | Repeat, no new items | All unchanged; run success; no duplicates |
| C | New HH vacancies appear | Those rows `created`; others unchanged |
| D | Known vacancy changed | In-place update; report `updated`; funnel status preserved |
| E | Vacancy absent from results | Not deleted; optional stale marker |
| F | HH archived/closed | Source-state update; keep history |
| G | Pagination interrupted | Run=`partial`; persist `last_page_completed`; **not** fake success |
| H | HH temporary unavailable / 403 | Run=`failed` with recovery code; no fake vacancies |
| I | Retry after partial | Resume/continue safely; idempotent creates/updates |
| J | Same external_id via different queries | Still one Vacancy; maybe link to multiple runs/contexts |

---

## 12. New / known / updated semantics

Product-facing (sync report + list filters), distinct from funnel `status`:

| Label | Meaning |
|---|---|
| **new** | First time this `(source, external_id)` entered Core **or** first seen by operator since import (MVP: Core created in this run / `status=new` and never opened — owner pick) |
| **known** | Already in Core before this run; unchanged |
| **updated** | Already in Core; material fields changed this run |
| **archived/closed** | HH source-state indicates closed/archived |

**Recommended MVP for “ещё не разбирал”:** use funnel `status=new` as “not yet
reviewed”, set automatically only on **create**. Sync must **not** reset
`reviewing/shortlisted/rejected` back to `new`. PB-04 decisions stay later.

Do not rely only on `created_at` of the sync run for UX.

---

## 13. Minimal Web UX (Vacancies workspace)

No new top-level workspace.

On **Вакансии**:

1. Show active search context summary (query + key filters).
2. CTA **«Обновить с HH»** / sync.
3. Last run: when, status, fetched / new / updated / known / errors.
4. Vacancy list refreshes with real HH rows.
5. Failure shows recovery language (not silent empty success).

Out of scope UI: scoring, decision buttons, SearchProfile studio, resume-derived
search builder.

---

## 14. Non-scope (hard)

- AI scoring / Ollama / embeddings / SCORING_SERVICE_FOUNDATION (R2.3+)
- score/verdict / detailed scoring
- vacancy decision «добиваться/отложить/отказаться» (PB-04 / R2.6)
- apply / negotiations / OSINT / outreach
- providers other than HH (PB-FUTURE-02)
- PB-FUTURE-01 resume-derived HH search
- auto-building search from ResumeVersion text

---

## 15. Product US / TECH-US / EXT

### US-02.1 — Search context for HH vacancy discovery

**Purpose:** operator defines bounded search parameters used for ingestion.  
**AC:** context persists across reload; shown on Vacancies; not mixed into
ResumeVersion.  
**Deps:** none beyond R2.1 complete.  
**Repos:** Core (+ Web).  
**Evidence:** Web shows context; API/CLI readback.

### US-02.2 — Manual HH vacancy sync into Core

**Purpose:** one operator action imports current HH results without copy-paste.  
**AC:** vacancies appear in Core/Web; report distinguishes new/known/updated;
repeat safe.  
**Deps:** US-02.1; HH acquisition transport decision.  
**Repos:** HH + Core + Web.  
**Evidence:** live or deterministic fixture run with observable counts.

### US-02.3 — Idempotent identity + update without destroying funnel state

**Purpose:** same HH id never duplicates; changes update; user status preserved.  
**AC:** matrix B/D/J green; Assessment/Application links survive update.  
**Deps:** Core upsert.  
**Repos:** Core (+ HH normalize).  
**Evidence:** automated tests + one live/fixture replay.

### TECH-US-02.T1 — HH acquisition adapter with honest failure

**Purpose:** encapsulate API and/or browser RO behind one provider; map 403/5xx
to recovery codes; support pagination + partial resume.  
**AC:** unavailable/forbidden ≠ fake success; page checkpoint stored.  
**Deps:** owner transport decision.  
**Repos:** HH.  
**Evidence:** unit + contract + live probe notes.

### TECH-US-02.T2 — Normalization allowlist + schema_version

**Purpose:** map only real HH fields; stable Core write contract.  
**AC:** incomplete items rejected; PII/contacts not required/stored from vacancy
cards beyond public posting fields.  
**Repos:** HH (+ Core schema if expanded).

### EXT-02.E1 — Semantic / cross-source dedupe

Deferred. Not MVP.

### EXT-02.E2 — HH saved searches as context source

Deferred until API capability proven.

### DEBT-02.D1 — README/ARCHITECTURE overclaim “vacancy sync implemented”

Docs should distinguish scaffold vs accepted product flow after R2.2 starts.

---

## 16. Suggested internal slices (vertical)

| Slice | Acceptance meaning |
|---|---|
| **R2.2.1** | Persist + show minimal VacancySearchContext (Core+Web); no HH fetch required |
| **R2.2.2** | HH acquisition path chosen & working for read (API unblocked **or** approved browser RO) + pagination/partial failure semantics |
| **R2.2.3** | Core upsert/update + richer normalize; identity dedupe; funnel status preserved |
| **R2.2.4** | End-to-end sync orchestration + new/known/updated report (CLI/HTTP) |
| **R2.2.5** | Vacancies Web sync UX (run summary + list refresh) |
| **R2.2.A** | Integrated acceptance / Gate evidence for R2.2 |

Do **not** start production slices until this decomposition is OWNER ACCEPTED and
open decisions below are resolved.

---

## 17. Acceptance target (R2.2 complete)

> Job Search по заданному search context получает вакансии из HeadHunter,
> идемпотентно нормализует и сохраняет их в Core, отличает новые от уже
> известных/обновлённых и показывает результат пользователю без copy-paste.

Must hold: safe replay; recoverable partial failure; stable source identity;
Vacancies list shows real HH vacancies; **no** Scoring required.

---

## 18. Repo impact (when implementation starts)

| Repo | Likely work |
|---|---|
| Core | search-context (+ sync-run) persistence; vacancy upsert/update; optional field/JSONB expansion; APIs |
| HH | acquisition adapter, filters/pagination, normalize, sync report, recovery codes |
| Web | search-context summary + sync CTA + run summary on Vacancies |
| Scoring | unchanged |
| Workspace | this decomposition + status alignment |

---

## 19. Risks / external constraints

1. **CRITICAL:** live `GET /vacancies` (and detail) currently **403** via working
   egress; same class as other HH EXTERNAL_BLOCKED endpoints.
2. Without an acquisition path, R2.2 product acceptance cannot complete.
3. Expanding Vacancy schema touches migrated historical rows — need careful
   nullability/backfill.
4. Treating funnel `status=new` as “unreviewed” must not fight existing operator
   habits on 400+ historical vacancies.
5. Browser RO vacancy search would be a significant new automation surface
   (rate limits, DOM fragility) — only if owner accepts after API path fails.

---

## 20. Open owner decisions

1. **Acquisition transport for R2.2 MVP**  
   Prefer unblock/fix official HH vacancies API **vs** approve browser RO search
   **vs** temporary fixture/manual-only (not product-complete).

2. **Search-context entity naming**  
   `VacancySearchContext` (recommended) **vs** reuse name `SearchProfile` for the
   same minimal object **vs** non-persisted CLI-only params for first vertical.

3. **Core schema expansion now vs later**  
   Typed salary/location/… columns in R2.2.3 **vs** JSONB `attributes` first.

4. **“New” product meaning**  
   Sync-created only **vs** funnel `status=new` as unreviewed badge (recommended
   combo: create→`status=new`; never reset reviewed statuses on re-sync).

5. **Missing-from-search behaviour**  
   Soft stale marker only (recommended) **vs** auto-archive.

6. **Detail fetch required in MVP?**  
   Search-snippet descriptions enough for list **vs** mandatory detail page
   before counting a vacancy as fully imported.

Default recommendation if owner says «го» on this doc without deltas:

- Decision 1: attempt API remediation first; browser RO only as explicit fallback  
- Decision 2: `VacancySearchContext` (not full SearchProfile)  
- Decision 3: JSONB `attributes` + keep current columns, expand later if needed  
- Decision 4: create→`new`; never reset reviewed  
- Decision 5: soft stale only  
- Decision 6: list payload first; detail enrichment as follow-up inside R2.2 if API allows

---

## 21. Final status framing

```text
R2.1 = COMPLETE · OWNER ACCEPTED · PUSHED

R2.2 DECOMPOSITION = READY FOR OWNER REVIEW

R2.2 production implementation = NOT STARTED

R2.3 = NOT STARTED
```
