# R2.2 — SearchProfile + HH vacancy ingestion / normalization / dedupe

**Status:** **READY FOR OWNER ACCEPTANCE** (docs-only; owner decisions incorporated)  
**Production implementation:** **NOT STARTED**  
**R2.1:** **COMPLETE · OWNER ACCEPTED · PUSHED**  
**R2.3:** **NOT STARTED**

**Canonical SoT:** Google Drive **Job Search** (Product Backlog, Roadmap, R2).  
**Evidence / decision date:** 2026-08-27.

This document is the accepted-shape decomposition for R2.2 after owner review
inputs. It does **not** authorize production code, migrations, or API changes
until **OWNER ACCEPTED**.

---

## 0. Status correction

```text
R2.1 = COMPLETE · OWNER ACCEPTED · PUSHED
R2.2 decomposition = READY FOR OWNER ACCEPTANCE
R2.2 production = NOT STARTED
R2.3 = NOT STARTED
```

---

## 1. Product goal

After R2.1:

```text
active HH account/session
  + active HH resume
  + local immutable ResumeVersion
```

R2.2:

```text
minimal SearchProfile
  → SearchRun (immutable criteria snapshot)
  → HeadHunter vacancy discovery
  → normalize
  → Core upsert (source + external_id)
  → created / updated / unchanged
  → observable result in «Вакансии»
```

**R2.2 does not score vacancies.** Scoring = **R2.3**.

Mapped PBIs: **PB-02** + minimal **PB-01 SearchProfile** criteria only.  
**Not** PB-FUTURE-01 (resume-derived HH search).

---

## 2. Owner decisions (accepted for this decomposition)

### 2.1 SearchProfile

R2.2 introduces a **minimal persisted SearchProfile**.

- Not ad-hoc CLI `--text` as product SoT.
- Separate from CandidateProfile / ResumeVersion:

| Entity | Meaning |
|---|---|
| CandidateProfile / ResumeVersion | кто кандидат / каким резюме представлен |
| SearchProfile | какие вакансии сейчас ищем |

- **Do not** auto-build SearchProfile from ResumeVersion.
- No full SearchProfile redesign — only criteria needed for R2.2 HH search.
- SearchProfile may remain **mutable**.
- **SearchProfileVersion is not required** in R2.2.

### 2.2 SearchRun

Persisted fact of one search execution. Minimum:

- `search_profile_id`
- `source = hh`
- **immutable criteria snapshot** (exact criteria used for this run)
- `started_at` / `finished_at`
- `status`: `success` | `partial` | `failed`
- `found` count
- `created` / new count
- `updated` count
- `unchanged` / known count
- `error` count
- pagination / progress metadata as needed

Optional provenance: capture current Candidate / ProfileVersion / ResumeVersion
ids at run time — **without** deriving search criteria from resume.

### 2.3 Vacancy identity / dedupe

Canonical MVP identity: **`(source, external_id)`**.

HH: `source = hh`, `external_id = HH vacancy id`.

No fuzzy / semantic / LLM dedupe across different ids. Republished HH vacancy
with a new id may be a separate Core Vacancy in MVP. Cross-id semantic dedupe =
future/debt (EXT), not an R2.2 blocker.

### 2.4 Vacancy upsert

Append-only create + `vacancy_exists` is insufficient.

For one `(source, external_id)`:

| Normalized source content | Outcome |
|---|---|
| same | **unchanged** |
| changed | **update** source-owned fields → **updated** |

Preserve: Core Vacancy UUID, Assessment / Application / Person links, and user
workflow `Vacancy.status`.

**Do not** use `Vacancy.status` for ingestion state.

- `Vacancy.status` = `new | reviewing | rejected | shortlisted` (user workflow)
- `created | updated | unchanged` = **SearchRun item outcomes**

Prefer a **separate ingestion/upsert contract** over overloading manual-create
idempotency semantics, unless a clean compatible extension is proven.

### 2.5 Source change detection

Deterministic **normalized `content_hash`** (or equivalent) over **source-owned
normalized fields only**. Exclude user-owned state (`Vacancy.status`, notes,
decisions, etc.).

### 2.6 Vacancy lifecycle

- Missing from one SearchRun result set → **do not** auto-change source state;
  **do not** treat as archived/closed; **do not** delete historical Core Vacancy.
- `archived` / `closed` only when HH explicitly confirms via detail/status /
  supported source signal.

### 2.7 HH transport

Live probe (2026-08-27, working egress): **`GET /vacancies` → HTTP 403**.

- Existing `HttpHhApi` = **implementation scaffold**, not proven R2.2 capability.
- Preferred transport: official HH API **if** correctly confirmed.
- Before vacancy-acquisition implementation: **bounded live capability
  verification** (endpoint, headers/UA, auth need, proxy/egress, pagination,
  403 reason if determinable, 429/rate-limit behaviour).
- Browser RO for vacancy search is **not** auto-approved (resume browser RO does
  not extend). If API remains unavailable/403 after correct probe → **STOP** for
  a separate owner decision on browser RO vacancy search. No silent fallback.

### 2.8 Pagination / partial failure

R2.2 is **not** one-page-limited. Successful pages may ingest; unfinished
pagination → SearchRun `status=partial` (not fake success). Retry safe via
identity + upsert.

### 2.9 New / known / updated

Per **SearchRun**:

| Outcome | Meaning |
|---|---|
| **new** (`created`) | Core Vacancy created for the first time |
| **updated** | Vacancy existed; source-owned normalized content changed |
| **known** (`unchanged`) | Vacancy existed; content unchanged |

Never conflate with `Vacancy.status`.

### 2.10 Web boundary

Use existing **«Вакансии»**. Operator sees:

- active SearchProfile summary
- «Найти вакансии» / «Обновить»
- last SearchRun time + totals (found / new / updated / known) + partial/error
- real HH vacancies in the list

No Scoring UI in R2.2.

---

## 3. Conflicts resolved

| Topic | Prior tension | Resolution |
|---|---|---|
| Entity name | `VacancySearchContext` vs `SearchProfile` | **SearchProfile** (minimal persisted) |
| CLI `--text` | scaffold as SoT | **Not** product SoT; SearchProfile + SearchRun are |
| Create-only Core | identity collisions / no update | **Separate upsert/ingestion contract** + `content_hash` |
| Missing from run | soft stale vs archive | **No auto source-state change**; archive only on explicit HH signal |
| “New” meaning | funnel `status=new` vs run outcome | Run outcome **created/new**; funnel status stays user-owned |
| HH API “works” | README/scaffold claim | Scaffold only; live **403** until capability proof |
| Browser fallback | tempting after 403 | **Forbidden** without separate OWNER DECISION |
| R2.1.A push in Google R2 tab | said not pushed | Workspace `5df713c` **pushed**; update Google Doc when convenient |

---

## 4. Final SearchProfile model proposal

Mutable, minimal, single-user MVP (one active profile is enough initially):

```text
SearchProfile
  - id
  - label (optional human name)
  - text: str                         # HH text query (required for MVP)
  - area_id: optional
  - salary: optional {from, to, currency}
  - experience: optional HH dictionary id
  - employment: optional HH dictionary id
  - schedule: optional HH dictionary id
  - search_field: optional            # name | company_name | description
  - order_by: optional                # default publication_time
  - only_with_salary: optional bool
  - page_size: int
  - max_pages: int
  - created_at / updated_at
```

Non-goals: SearchProfileVersion; multi-profile studio; resume-derived builder;
auto-sync from ResumeVersion.

---

## 5. Final SearchRun proposal

```text
SearchRun
  - id
  - search_profile_id
  - source = "hh"
  - criteria_snapshot: JSON           # immutable copy of criteria used
  - candidate_context_snapshot?: JSON # optional ids only (profile/resume)
  - started_at / finished_at
  - status: success | partial | failed
  - found_count
  - created_count                     # new
  - updated_count
  - unchanged_count                   # known
  - error_count
  - pagination: {
      last_page_completed?,
      pages_fetched?,
      per_page?,
      hh_found?,
      hh_pages?
    }
  - error_code / recovery_hint?: optional
```

SearchProfile may change after a run; historical truth lives in
`criteria_snapshot`.

---

## 6. Final Vacancy upsert / update proposal

### Identity

`(source, external_id)` unique — REUSE existing constraint.

### Ingestion contract (preferred)

Dedicated upsert path (name TBD at implementation), e.g. conceptual:

```text
POST /api/v1/vacancies/upsert   # or HH-facing ingest endpoint into Core
body: normalized source-owned vacancy fields
→ { vacancy, outcome: created | updated | unchanged }
```

Manual `POST /api/v1/vacancies` + Idempotency-Key remains for manual/Web add;
do not break it without need.

### Change detection

1. Normalize allowlisted source fields.
2. Compute `content_hash` over canonical normalized source payload.
3. Lookup by `(source, external_id)`:
   - missing → insert (`created`); default funnel `status=new` only on create
   - present + same hash → (`unchanged`); may bump `last_seen_at` if stored
   - present + different hash → update source-owned fields + hash (`updated`);
     preserve UUID, relations, `Vacancy.status`

### Source-owned vs user-owned

| Source-owned (hash + upsert) | User-owned (never hashed / never overwritten by ingest) |
|---|---|
| title, url, description, company link fields, salary/area/employment/…, HH timestamps, HH archived/closed when explicit | `Vacancy.status`, future decisions/notes |

### Schema expansion

Implementation may store extra HH fields as typed columns and/or JSONB
`attributes` + `content_hash` + optional `last_seen_at`. Exact storage shape is
an implementation detail inside R2.2.3 as long as upsert invariants hold.

---

## 7. Exact new / updated / known semantics

Within one SearchRun:

| Term | Definition |
|---|---|
| **new** | upsert outcome `created` — first Core row for `(source, external_id)` |
| **updated** | upsert outcome `updated` — hash changed; source fields rewritten |
| **known** | upsert outcome `unchanged` — existed; hash identical |

Web run summary uses these counts. List filtering by run outcome is optional;
funnel filters remain on `Vacancy.status`.

---

## 8. Final HH transport status

| Claim | Status |
|---|---|
| Official API preferred | Yes |
| Scaffold `HttpHhApi` / CLI `vacancies sync` | Exists |
| Live `GET /vacancies` (public + Bearer, egress) | **403 forbidden** (2026-08-27) |
| Live `/me`, `/dictionaries`, `/areas` | 200 |
| Proven R2.2 acquisition capability | **No** |
| Browser vacancy search | **Not approved**; separate OWNER DECISION if API stays blocked |

**Gate before R2.2.2 implementation beyond fixtures:** bounded capability
verification document/result. If still 403/unavailable → STOP for owner
browser-RO decision.

---

## 9. Product US / TECH-US / EXT

### US-02.1 — Minimal SearchProfile

Operator defines and persists HH search criteria.  
**AC:** survives reload; shown on Vacancies; not derived from ResumeVersion; CLI
`--text` is not SoT.  
**Repos:** Core (+ Web read/edit).  
**Evidence:** API/CLI + Web summary.

### US-02.2 — SearchRun execution with honest status

Operator starts a run; system records snapshot + counts + success/partial/failed.  
**AC:** criteria snapshot immutable; partial ≠ success; optional candidate
context ids only.  
**Repos:** Core + HH orchestration.  
**Evidence:** persisted SearchRun + report.

### US-02.3 — Source-identity upsert into Vacancy list

HH hits become Core vacancies without duplicates; changes update source fields.  
**AC:** created/updated/unchanged; UUID/relations/`Vacancy.status` preserved.  
**Repos:** Core (+ HH normalize).  
**Evidence:** tests + fixture/live run.

### US-02.4 — Vacancies Web flow

Operator sees profile, runs search, understands last run, sees HH vacancies.  
**AC:** counts + partial/error visible; no scoring UI.  
**Repos:** Web (+ proxies).  
**Evidence:** live UI checklist.

### TECH-US-02.T1 — HH acquisition + capability proof

Prove or refute official vacancy API; pagination; recovery codes; no silent
browser.  
**Repos:** HH.  
**Evidence:** probe notes + provider contract tests.

### TECH-US-02.T2 — Normalize + content_hash

Allowlist mapping; deterministic hash; reject incomplete items.  
**Repos:** HH (+ Core hash storage).

### EXT-02.E1 — Semantic / cross-id / cross-source dedupe

Deferred.

### EXT-02.E2 — HH saved searches as SearchProfile source

Deferred until API capability proven.

### EXT-02.E3 — Browser RO vacancy search

Deferred; requires explicit OWNER DECISION after API probe failure.

### DEBT-02.D1 — Docs overclaim “vacancy sync implemented”

Correct scaffold vs accepted product language when R2.2 implementation starts.

---

## 10. Internal slices

Owner-preferred sequence (adopted). Prior draft used `VacancySearchContext` /
`VacancySyncRun` naming and mixed context persistence with weaker upsert
framing; **same vertical idea**, renamed and tightened to SearchProfile +
SearchRun + explicit capability-proof gate on R2.2.2.

| Slice | Acceptance meaning |
|---|---|
| **R2.2.1** | Persisted minimal **SearchProfile** + **SearchRun** model/API (no live HH required) |
| **R2.2.2** | HH vacancy acquisition transport + pagination; **capability proof first**; browser only after separate owner decision if API unavailable |
| **R2.2.3** | Normalized Vacancy **upsert**: identity + `content_hash` + created/updated/unchanged |
| **R2.2.4** | End-to-end SearchRun: SearchProfile → HH → pages → Core → run summary / recovery |
| **R2.2.5** | Human-readable Web flow on **«Вакансии»** |
| **R2.2.A** | Integrated R2.2 acceptance / Gate evidence |

Production slices start only after this decomposition is **OWNER ACCEPTED**.

---

## 11. Acceptance target (R2.2 complete)

> Job Search по минимальному SearchProfile запускает SearchRun, получает
> вакансии из HeadHunter (когда transport confirmed), идемпотентно upsert’ит их
> в Core по `(source, external_id)`, отличает new / updated / known и показывает
> результат в «Вакансии» без copy-paste.

Must hold: safe retry; partial ≠ fake success; user workflow status preserved;
no Scoring.

---

## 12. Repo impact (when implementation starts)

| Repo | Work |
|---|---|
| Core | SearchProfile, SearchRun, vacancy upsert + content_hash, APIs |
| HH | capability verification, acquisition adapter, normalize, run orchestration |
| Web | SearchProfile summary, find/update CTA, last-run summary on Vacancies |
| Scoring | unchanged |
| Workspace | status / plan alignment |

---

## 13. Risks

1. Live vacancies API **403** blocks product acceptance until transport resolved.
2. Historical ~400+ vacancies must remain compatible with upsert/hash backfill.
3. Browser RO search is large surface — only with explicit owner approval.
4. Overloading manual create idempotency would be fragile — prefer separate
   ingest contract.

---

## 14. Open owner decisions (remaining)

1. **After capability verification:** if official `GET /vacancies` remains
   403/unavailable — allow authenticated/public **browser RO vacancy search**?
   (Default until answer: **no**.)

2. **Detail enrichment in MVP:** list/search payload only vs mandatory
   `GET /vacancies/{id}` when API works. (Default proposal: list-first; detail
   as follow-up inside R2.2 if transport allows.)

No other blocking naming/identity/upsert/lifecycle decisions remain for
acceptance of this decomposition.

---

## 15. Non-scope (hard)

- AI scoring / Ollama / embeddings / SCORING_SERVICE_FOUNDATION
- score/verdict / detailed scoring / PB-04 decisions
- apply / negotiations / OSINT / outreach
- providers other than HH
- PB-FUTURE-01 resume-derived search
- silent browser vacancy fallback
- SearchProfileVersion / full SearchProfile redesign
- fuzzy cross-id dedupe

---

## 16. Final framing

```text
R2.1 = COMPLETE · OWNER ACCEPTED · PUSHED

R2.2 DECOMPOSITION = READY FOR OWNER ACCEPTANCE

R2.2 production implementation = NOT STARTED

R2.3 = NOT STARTED
```
