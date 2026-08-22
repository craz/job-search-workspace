# Job Search Legacy Data Migration

## Status

| Field | Value |
|---|---|
| **Slice** | PB-DATA-00.4 — Dry-run implementation **COMPLETE** |
| **Date** | 2026-08-22 (UTC+3) |
| **Prior mapping** | PB-DATA-00.2 @ `b66d13d` · safety contract @ `6737b8a` |
| **Next slice** | PB-DATA-00.5 — Backup + first supported migration APPLY |

| **Source** | `/data/Projects/job_search` (read-only) |
| **Target** | `/data/Projects/job_search_ref` → Core PostgreSQL |
| **Source policy** | Read-only; no writes to source during inventory/mapping |

---

## 1. Executive summary

**Primary product database:** single SQLite file  
`/data/Projects/job_search/data/job_search.db` (792 KiB, last modified **2026-07-31 14:21**).

**Schema version:** SQLite `PRAGMA user_version = 4` (migrations `001`–`004` in legacy code).

**Historical window:** roughly **2025-08-29** (oldest daily metric) through **2026-07-31** (latest company/person updates). Core funnel activity concentrates **2026-04-30 .. 2026-07-30** (vacancies/applications).

**Scale (authoritative product tables):** ~**511** vacancies, **407** applications, **1366** companies, **24** people, **81** daily metrics, **2** hypotheses, **28** content log rows.

**Main surprises / risks:**

1. **Scoring is split across stores:** only **16** vacancies have embedded `reason/risk/action` in SQLite, while **`vacancy_scores.jsonl`** holds **1009** score records for **870** unique HH vacancy IDs — **850** of those IDs are **not** present in SQLite vacancies (only **20** overlap by HH ID).
2. **Companies >> vacancies:** **1366** companies (mostly `track_status=watch`) vs **511** vacancies — large watchlist, not all tied to funnel rows.
3. **Applications lack outcome data:** **406/407** applications have `result IS NULL`.
4. **Large non-DB artifacts:** `hh_snapshots/` ~**1.7 GiB**, `chatgpt_export_raw/` ~**1.1 GiB**, browser profile ~**5.6 GiB** — mostly **not** canonical product history.
5. **No legacy `data/companies/` markdown tree** on disk (README mentions it; directory absent) — companies already in SQLite.
6. **Resume/profile context** exists as **text files only** (`resume.txt`, `resume_summary.txt`); no CandidateProfile table in SQLite.

---

## 2. Storage inventory

Classification: **A** Product · **B** Derived/rebuildable · **C** Cache · **D** Runtime state · **E** Secrets · **F** Code/config

| Path | Class | Type | Approx. size | In migration scope? | Notes |
|---|---|---|---:|---|---|
| `data/job_search.db` | A | SQLite 3 | 792 KiB | **Yes** | Canonical relational history |
| `data/vacancy_scores.jsonl` | B | JSONL | 3.3 MiB (1009 lines) | **Yes (review)** | Full scoring payloads; mostly HH IDs not in DB |
| `data/vacancy_fetch_queue.jsonl` | B | JSONL | 12 MiB (2085 lines) | Optional | Fetch/scoring pipeline queue; rebuildable |
| `data/scoring_batch2_vacancies.jsonl` | B | JSONL | 54 KiB (10 lines) | Optional | Benchmark/batch artifact |
| `data/scoring_batch2_scores.jsonl` | B | JSONL | 0 B | No | Empty |
| `data/vacancy_scoring_queue.jsonl` | B | JSONL | 0 B | No | Empty |
| `data/archive/reset-20260702-144551/*` | B | JSONL archive | 56 KiB | No | Pre-reset copy of scores/queues |
| `data/osint/*.json` | B | JSON (4 files) | 32 KiB | **Should review** | OSINT harvest keyed by HH vacancy id |
| `data/resume.txt` | A | text | 20 KiB | **Yes** | Full resume text for scoring/HH context |
| `data/resume_summary.txt` | A | text | 2 KiB | **Yes** | Short resume summary for Ollama models |
| `data/hh_resumes/` | A | dir | empty | Optional | Intended HH API resume export location |
| `data/cover-letter.txt` | A | text | 2 KiB | Optional | Single cover letter template, not per-application |
| `data/applications` cover letters in DB | A | SQLite TEXT | 93 rows | **Yes** | `applications.cover_letter_text` |
| `data/telegram_channel_messages.jsonl` | B | JSONL | 52 KiB (29 lines) | Optional | Channel mirror; related to Content |
| `data/content_logs` + draft paths | A | SQLite + files | 28 rows | **Should review** | Draft paths may point to missing files |
| `data/hh_snapshots/` | B | HTML/JSON | **1.7 GiB** (1005 files) | Optional | Debug captures (apply, negotiations) |
| `data/chatgpt_export_raw/` + derived | B | export | **1.1 GiB** | No (product) | Personal ChatGPT export |
| `data/board.html` | B | HTML | 7.3 MiB | No | Generated dashboard snapshot |
| `data/score_*.json`, benchmarks | B | JSON | &lt;100 KiB | No | Model comparison artifacts |
| `data/hh_token.json`, `hh_app_token.json` | E | JSON tokens | small | **DO NOT MIGRATE** | HH OAuth/app credentials |
| `data/hh_browser_profile/` | E/D | Chromium | **~5.6 GiB** | **DO NOT MIGRATE** | Cookies/session state |
| `data/hh_chats.json` | E | JSON | 932 KiB | **DO NOT MIGRATE** | HH chat dump; PII |
| `data/ollama/` | C | Modelfiles | 116 KiB | No | Regenerate via Ollama |
| `data/logs/`, `apply_*.log`, `hermes_*` | D | logs | ~4 MiB | No | Operational logs |
| `data/fetch-all.state` | D | state | 102 B | No | Scoring cursor |
| `data/settings` (SQLite) | A/D | key/value | 17 rows | Partial | Mix of product config + operational cursors |
| `tmp/osint-tools/` | B/C | CSV/JSON | small | No | Ad-hoc OSINT experiments |
| `.venv/.../data/job_search.db` | C | SQLite | copy | No | Dev/test copy; not authoritative |
| PostgreSQL | — | — | — | — | **Not used** in legacy runtime |

**No PostgreSQL** found in legacy product runtime. All normalized history is SQLite + adjacent files under `data/`.

---

## 3. Entity inventory

Business entities inferred from **code + DB** (`models.py`, migrations, repositories).

### 3.1 Vacancy

| Attribute | Value |
|---|---|
| Storage | `vacancies` table |
| Legacy PK | `id` INTEGER AUTOINCREMENT |
| External IDs | HH vacancy ID parseable from `url` for **401/511** rows (`/vacancy/{id}`) |
| Count | **511** |
| Date range | `created_at` **2026-04-30 .. 2026-07-30** |
| Authoritative? | **Yes** — core funnel entity |
| Key fields | `title`, `company`, `company_id`, `source`, `url`, `status`, `priority`, `salary_*`, `work_format`, `cohort`, `relevance`, `notes`, `status_updated_at`, embedded `reason/risk/action` |
| Status values (observed) | `viewed` 208, `applied` 150, `reject` 110, `interview` 30, `archived` 6, `found` 4, `prioritized` 3 |
| Source values (observed) | `hh_sync` 205, `hh_apply` 178, `company_track` 91, `hh` 19, `hh_bot` 16, `manual` 1, `hh_resume_view` 1 |
| Notes | **12** rows missing `company_id` (denormalized `company` text still present). **0** duplicate URLs among non-empty URLs. |

### 3.2 Company

| Attribute | Value |
|---|---|
| Storage | `companies` table |
| Legacy PK | `id` |
| External IDs | `employer_id` (HH) on **1321/1366** rows; unique index enforced |
| Count | **1366** |
| Date range | **2026-06-08 .. 2026-07-31** |
| Authoritative? | **Yes** for employer watchlist + linked vacancies |
| Key fields | `name`, `aliases`, `employer_id`, `hh_url`, `track_status`, `sector`, `notes`, vacancy counters, optional `description_*`, `site_url` |
| track_status | `watch` 1093, `active` 272, `contacted` 1 |
| Notes | Rich description populated on **5** companies; `site_url` on **7**. Many watchlist entries without vacancies. |

### 3.3 Application (outreach / apply history)

| Attribute | Value |
|---|---|
| Storage | `applications` table |
| Legacy PK | `id` |
| FK | `vacancy_id` → `vacancies.id` (enforced; **0** orphans) |
| Count | **407** (exactly **1** application per vacancy max) |
| Date range | `applied_at` **2026-06-08 .. 2026-07-02** |
| Authoritative? | **Yes** — apply history |
| Key fields | `applied_at`, `resume_version`, `cover_letter_version`, `cover_letter_text`, `result`, `next_action`, `next_action_date` |
| Notes | **406** rows with `result` NULL; **93** with non-empty `cover_letter_text`; all **407** have `resume_version`. |

### 3.4 Assessment / scoring (split representation)

| Representation | Storage | Count | Notes |
|---|---|---:|---|
| Embedded assessment columns | `vacancies.reason/risk/action` | **16** each | Board/CLI sync subset |
| Full scoring runs | `data/vacancy_scores.jsonl` | **1009** lines / **870** unique HH IDs | Nested `score` object: `score`, `verdict`, `reasons`, `mismatches`, `strengths`, `method`, `scored_at`, … |
| Settings cursor | `settings.last_scored_vacancy_id` | — | Operational, not history |

**Verdicts in JSONL:** `apply`, `maybe`, `skip`. **Methods:** `ollama`, `manual+ollama`, `rules`.  
**Resume source in JSONL:** `data/resume.txt` only.

**Critical:** JSONL scores use **HH vacancy_id** strings; overlap with SQLite vacancies is only **20/870** scored IDs. Majority of scores reference vacancies **not imported** into SQLite.

### 3.5 Person / contact

| Attribute | Value |
|---|---|
| Storage | `people` table (migration 004) |
| Legacy PK | `id` |
| FKs | `company_id` → companies (**0** orphans); optional `vacancy_id` → vacancies (**0** orphans when set) |
| Count | **24** |
| Date range | **2026-07-29 .. 2026-07-31** |
| External | `hh_vacancy_id` on all rows (4 distinct values) |
| Roles | `hiring_manager`, `peer`, `referral`, `recruiter` |
| Sources | `manual`, `company_site`, `habr`, `linkedin`, `web`, … |
| Related files | `data/osint/{134532490,134905188,135508094,135691214}.json` |

### 3.6 Daily metrics

| Attribute | Value |
|---|---|
| Storage | `daily_metrics` |
| PK | `date` TEXT |
| Count | **81** |
| Date range | **2025-08-29 .. 2026-07-23** |
| Notes | All rows have `views_total`; only **17** have non-null `applications` column populated |

### 3.7 Hypothesis

| Attribute | Value |
|---|---|
| Storage | `hypotheses` |
| Count | **2** (both `status=active`) |
| Date range | **2026-06-09 .. 2026-06-23** |

### 3.8 Content / Telegram log

| Attribute | Value |
|---|---|
| Storage | `content_logs` |
| Count | **28** (**20** published, **8** drafts) |
| Date range | **2026-06-04 .. 2026-07-23** |
| Notes | **`linked_type` NULL** on all rows; `draft_path` references not verified on disk in this slice |

### 3.9 Settings (operational / config)

| Attribute | Value |
|---|---|
| Storage | `settings` key/value |
| Count | **17** keys |
| Examples | `search_start_date`, `channel_handle`, `channel_name`, scoring cursors, daily apply counters, `resume_strategy`, `hh_chats_ignored` |
| Notes | Mix of **product config** and **machine cursors** — not all belong in Core domain |

### 3.10 Resume / candidate profile (files only)

| Attribute | Value |
|---|---|
| Storage | `data/resume.txt`, `data/resume_summary.txt` |
| DB entity | **None** |
| Notes | Used by Ollama scoring models; no versioned Resume/CandidateProfile table |

### 3.11 Entities **not** found in source

No SQLite tables or authoritative files for: SearchProfile, CandidateProfile, ProfileVersion, ResumeVersion, user decision on vacancy, hiring pipeline, Offer, SearchCycle, explicit Assessment table (only columns + JSONL).

---

## 4. Relationships

### Explicit FKs (SQLite)

```text
applications.vacancy_id → vacancies.id     (407 rows, 0 orphans)
people.company_id       → companies.id     (24 rows, 0 orphans)
people.vacancy_id       → vacancies.id     (optional; 0 orphans when set)
vacancies.company_id    → companies.id     (499/511 linked; 12 NULL)
```

### Implicit / external linkages

| Link | Mechanism | Quality |
|---|---|---|
| Vacancy ↔ HH | URL `/vacancy/{id}` | **401** parseable |
| Company ↔ HH | `companies.employer_id` | **1321** rows |
| People ↔ HH vacancy | `people.hh_vacancy_id` | 4 distinct IDs, matches OSINT JSON filenames |
| Scores ↔ Vacancy | JSONL `score.vacancy_id` (HH string) | **20** match DB URLs; **850** scores without DB row |
| People ↔ OSINT files | HH id in filename | 4 files ↔ 4 `hh_vacancy_id` values |
| Content ↔ domain | `content_logs.linked_type/id` | **Unlinked** (all NULL) |
| Application ↔ cover letter | inline TEXT | 93 stored texts |

### Denormalization

- `vacancies.company` text retained alongside `company_id`
- `company_track` vacancies may use **employer page URLs** (44/91) instead of vacancy URLs

**Broken/ambiguous:** none detected at FK level; scoring JSONL ↔ SQLite vacancy linkage is **incomplete by design** (scores captured for pool beyond imported vacancies).

---

## 5. External IDs and provenance

| ID type | Location | Coverage |
|---|---|---|
| Legacy SQLite integer IDs | all tables | internal only; not portable |
| HH vacancy ID | `vacancies.url`, `people.hh_vacancy_id`, JSONL scores | primary external vacancy key |
| HH employer ID | `companies.employer_id` | 1321 companies |
| HH employer URL | `companies.hh_url`, some vacancy URLs | partial |
| Application source | `vacancies.source` | hh_sync, hh_apply, company_track, … |
| Scoring method | JSONL `score.method` | ollama / rules / manual+ollama |
| Scoring timestamp | JSONL `score.scored_at`, `vacancy.captured_at` | per score line |
| Resume provenance | JSONL `resume_source` | path string |
| Telegram | `content_logs.telegram_message_id` | when published |
| Settings search anchor | `search_start_date` = `2025-08-29` | metrics baseline |

**For later idempotency:** prefer `(source, external_id)` mapping using HH vacancy/employer IDs where stable; preserve legacy SQLite IDs as provenance metadata during import.

---

## 6. Historical value classification

| Dataset | Classification | Rationale |
|---|---|---|
| `job_search.db` — vacancies, applications, companies, people, metrics, hypotheses | **MUST_PRESERVE** | Core search history |
| `applications.cover_letter_text` | **SHOULD_PRESERVE** | Irreplaceable apply context (93 rows) |
| `resume.txt`, `resume_summary.txt` | **MUST_PRESERVE** | Profile context for R1/R2 |
| `vacancy_scores.jsonl` | **SHOULD_PRESERVE** | Richest scoring history; mostly off-DB IDs |
| `data/osint/*.json` | **SHOULD_PRESERVE** | Tied to people research (small) |
| `content_logs` | **OPTIONAL** | Content service deferred; small row count |
| `settings` (product keys) | **OPTIONAL** | Selective import; exclude cursors |
| `vacancy_fetch_queue.jsonl` | **REBUILDABLE** | Pipeline queue; can re-run fetch |
| Scoring benchmarks / compare JSON | **REBUILDABLE** | Experiments |
| `hh_snapshots/` | **OPTIONAL** | Debug; huge; low product value |
| `chatgpt_export_*` | **DO_NOT_MIGRATE** (as product data) | Personal export, not domain model |
| HH tokens, browser profile, chats | **DO_NOT_MIGRATE** | Secrets / session / PII |
| Logs, Hermes audit, generated `board.html` | **DO_NOT_MIGRATE** | Operational / disposable |
| `archive/reset-*` | **DO_NOT_MIGRATE** | Superseded snapshot |

---

## 7. Data quality observations

| Issue | Evidence |
|---|---|
| Missing company link | 12 vacancies without `company_id` |
| Sparse assessment columns | 16/511 vacancies with reason/risk/action |
| Scoring ↔ DB gap | 850 scored HH IDs absent from SQLite |
| Application outcomes empty | 406/407 `result` NULL |
| Content linkage absent | all `content_logs.linked_type` NULL |
| Metrics sparsity | applications metric populated 17/81 days |
| Duplicate applications | none (max 1 per vacancy) |
| Duplicate employer_id | none among non-empty IDs |
| URL duplicates | none among non-empty vacancy URLs |
| Mixed Latin/Cyrillic relevance grades | `A-` vs `А-` entries |

No malformed JSON observed in sampled `vacancy_scores.jsonl` lines. No orphan FK rows detected.

---

## 8. Real vs test / demo data

| Check | Result |
|---|---|
| Title/company keywords `test`, `smoke`, `demo` | **0** matches |
| Date ranges | Consistent real search period 2026 Q2–Q3 |
| Volume | Hundreds of real HH URLs and applications |

**Conclusion:** No reliable test/demo partition found. Data appears to be **real operational history**.

**MANUAL REVIEW NEEDED:** whether all **1093 watch-only companies** should migrate vs prune during mapping (volume vs value).

---

## 9. Non-database artifacts

| Location | Count / size | Linked to DB? |
|---|---|---|
| `resume.txt`, `resume_summary.txt` | 2 files | Used by scoring; no DB FK |
| `cover-letter.txt` | 1 template | Not per-row |
| `data/osint/*.json` | 4 files | HH ids match `people.hh_vacancy_id` |
| `telegram_channel_messages.jsonl` | 29 lines | Thematic overlap with `content_logs` |
| `telegram_draft_yesterday.md` | 1 file | Draft artifact |
| `hh_snapshots/` | 1005 files, 1.7 GiB | Debug; filenames include vacancy ids |
| `chatgpt_export_raw/` | large export | Not linked to SQLite |
| `data/covers/` | **0** files (dir missing or empty) | README mentions optional export |

**Not copied or inspected for content** (PII/secrets policy).

---

## 10. Migration scale

| Metric | Value |
|---|---|
| SQLite file size | **792 KiB** |
| Total SQL rows (product tables) | **~2415** (511+407+1366+24+81+2+28) |
| JSONL score records | **1009** (870 unique HH vacancies) |
| JSONL fetch queue lines | **2085** |
| OSINT JSON files | **4** |
| Resume text files | **2** |
| Relevant historical disk (MUST+SHOULD) | **~4–5 MiB** (DB + scores + osint + resumes) |
| Total `data/` on disk | **~8+ GiB** (dominated by browser profile, snapshots, ChatGPT export) |

**Assessment:** SQL volume is **small** — simple transactional import feasible. **JSONL scoring merge** is the main complexity (870 external keys, weak DB overlap), not raw size.

---

## 11. Unknowns from DATA-00.1 — resolved in §14–§21

Section 11 open questions from inventory are answered in mapping sections below. Product decisions are **locked in §23**.

---

## 12. Next step (historical)

Superseded by **§22**.

---

## 13. Target model inventory (job_search_ref Core)

Verified against `services/core/src/job_search_core/models.py`, `schemas.py`, Alembic migrations (7 revisions). **No** CandidateProfile, ResumeVersion, SearchCycle, Offer, or Content tables exist.

| Target entity | Table | PK | Unique keys | Required fields | Nullable / optional | Relationships |
|---|---|---|---|---|---|---|
| **Company** | `companies` | UUID | `(source, external_id)` | `name`, `source`, `external_id` | `website_url` | ← Vacancy, Person |
| **Vacancy** | `vacancies` | UUID | `(source, external_id)`, `idempotency_key` | `company_id`, `source`, `external_id`, `title`, `url`, `idempotency_key`, `request_fingerprint` | `description` | FK → Company **required**; → Application, Person, Assessment |
| **Application** | `applications` | UUID | `(source, external_id)`, `idempotency_key` | `vacancy_id`, `source`, `external_id`, `applied_at`, … | `result`, cover letter fields, `next_action*` | FK → Vacancy |
| **Person** | `people` | UUID | `(source, external_id)`, `idempotency_key` | `company_id`, `source`, `external_id`, `full_name`, `role` | `vacancy_id`, `title`, `url`, `confidence`, `notes` | FK → Company; optional Vacancy |
| **Assessment** | `assessments` | UUID | `(source, external_id)`, `idempotency_key` | `vacancy_id`, `source`, `external_id`, `relevance_score`, `verdict`, `reason`, `action`, `model`, `prompt_version`, `assessed_at` | `risk` | FK → Vacancy |
| **DailyMetric** | `daily_metrics` | `metric_date` (date) | PK = date | none strictly (all metric cols nullable) | all counters + `notes` | standalone |
| **Hypothesis** | `hypotheses` | UUID | `(source, external_id)`, `idempotency_key` | `source`, `external_id`, `title` | `description`, `test_size`, `metric`, `result` | standalone |

**Enums (target):**

- `VacancyStatus`: `new`, `reviewing`, `rejected`, `shortlisted`
- `ApplicationResult`: `reply`, `interview`, `rejected`, `offer`
- `PersonRole`: `hiring_manager`, `recruiter`, `referral`, `peer`
- `PersonStatus`: `new`, `researching`, `contacted`, `replied`, `dropped`
- `HypothesisStatus`: `active`, `done`
- `AssessmentVerdict`: `apply`, `maybe`, `skip`

**Write path:** HTTP `/api/v1/*` + idempotency header; Company created **only** implicitly via `VacancyCreate` (same `source` + `company_external_id`) or must pre-exist for Person. No standalone Company POST in current API.

**Legacy provenance gap:** Core has **no** generic `legacy_id` / JSON metadata column. Provenance must use `(source, external_id)` encoding (§17).

---

## 14. Source → target mapping (entity level)

| Legacy source | Legacy entity | Rows | Target | Status | Identity key | Relationship strategy | Notes |
|---|---|---:|---|---|---|---|---|
| `job_search.db` | `companies` (referenced) | **323** | `Company` | **SUPPORTED_NOW** | `(source, external_id)` — see §17 | Created before/with Vacancy/Person | 320 linked from vacancies + 3 people-only |
| `job_search.db` | `companies` (watch-only) | **1043** | `Company` | **DEFERRED** | HH `employer_id` when present | N/A in first slice | §23.1 — not DROP |
| `job_search.db` | `vacancies` (with `company_id`) | **499** | `Vacancy` | **SUPPORTED_NOW** | HH id from URL or `legacy_job_search` fallback | FK → Company | 401 with HH `/vacancy/{id}` |
| `job_search.db` | `vacancies` (no `company_id`) | **12** | `Vacancy` | **DEFERRED** | bot path or HH id | No synthetic Company | §23.1 |
| `job_search.db` | `applications` | **407** | `Application` | **SUPPORTED_NOW** | `application-{id}` @ `legacy_job_search` | FK → imported Vacancy | 406 with `result` NULL — valid |
| `job_search.db` | `people` | **24** | `Person` | **SUPPORTED_NOW** | `person-{id}` @ `legacy_job_search` | FK → Company (+ optional Vacancy) | Roles/status map directly |
| `job_search.db` | `daily_metrics` | **81** | `DailyMetric` | **SUPPORTED_NOW** | `metric_date` | Independent | All 81 incl. pre-2026-06-04 §23.1 |
| `job_search.db` | `hypotheses` | **2** | `Hypothesis` | **SUPPORTED_NOW** | `hypothesis-{id}` @ `legacy_job_search` | Independent | Both `active` |
| `job_search.db` | embedded `reason/risk/action` | **16** | `Assessment` | **DEFERRED** | — | — | No synthetic score/verdict §23.1 |
| `vacancy_scores.jsonl` | scores linked to SQLite (cat. **A**) | **20** HH | `Assessment` | **SUPPORTED_NOW** | `{hh_id}` @ `legacy_job_search_scoring` | FK → existing Vacancy | Latest per HH §23.5 |
| `vacancy_scores.jsonl` | scores off-DB (cat. **B**) | **850** HH / **988** lines | Vacancy + `Assessment` | **DEFERRED** | HH vacancy id | — | R2 / PB-02–03 §23.1 |
| `vacancy_scores.jsonl` | insufficient (cat. **C**) | **0** | — | — | — | — | None found |
| `data/osint/*.json` | OSINT raw harvest | **4** files | — | **REBUILDABLE** | HH vacancy id filename | Person already in SQLite | Do not stuff raw JSON into Person |
| `resume.txt`, `resume_summary.txt` | profile text | **2** files | CandidateProfile / ResumeVersion | **NEEDS_TARGET_MODEL** | — | Used by historical scoring | R1 target concept |
| `content_logs` | Telegram/draft journal | **28** | Content journal | **NEEDS_TARGET_MODEL** | — | Content service deferred | `linked_type` NULL |
| `telegram_channel_messages.jsonl` | channel mirror | **29** lines | Content | **NEEDS_TARGET_MODEL** | — | Adjacent to Content | Not Core |
| `settings` | key/value | **17** | — | **DROP_INTENTIONALLY** | — | Operational cursors / local config | Not domain history |
| `vacancy_fetch_queue.jsonl` | fetch queue | **2085** | — | **REBUILDABLE** | — | — | Pipeline artifact |
| `hh_snapshots/`, logs, tokens, browser profile, ChatGPT export | various | large | — | **DROP_INTENTIONALLY** | — | — | See §2 |

### 14.1 Watch-only companies (legacy semantics)

Legacy `companies.track_status` (`watch` | `active` | `contacted` | `pass`) is a **user company tracker** (CLI `company show/set/sync`). Companies are created on first lookup; HH `employer_id` and vacancy counters are often filled by **`company sync`** / HH API, not only manual intent.

| Bucket | Count | Semantics |
|---|---:|---|
| **A** Linked to Vacancy | **320** distinct companies | Used in real funnel — **SUPPORTED_NOW** |
| **B** Linked to Person only | **3** | OSINT contacts — **SUPPORTED_NOW** |
| **C** Watch-only (no vac, no person) | **1043** (**1042** `watch`, **1022** with `employer_id`) | **DEFERRED** in first slice §23.1 — source preserved |

**Locked decision:** first slice imports **323 referenced companies only**. **1043** watch-only rows are **DEFERRED**, not DROP_INTENTIONALLY; legacy source unchanged.

---

## 15. Field transformations (SUPPORTED_NOW only)

Non-trivial mappings only. Trivial direct copies omitted.

### Company (from legacy `companies`, referenced subset)

| Legacy field | Target field | Transform | Validation |
|---|---|---|---|
| `employer_id` | `external_id` | direct when non-empty | unique per `source` |
| (no employer_id) | `external_id` | `company-{sqlite_id}` | |
| `name` | `name` | direct | max 255 |
| `site_url` | `website_url` | direct URL | optional PUT if vacancy path skipped |
| `source` (implicit) | `source` | `hh` if employer_id else `legacy_job_search` | §23.8 |
| `track_status`, descriptions, HH counters | — | **omit** | no target columns |

### Vacancy (legacy `vacancies` with resolvable company)

| Legacy field | Target field | Transform | Validation |
|---|---|---|---|
| URL `/vacancy/{id}` | `external_id` | capture HH id | 401 rows |
| non-HH URL / bot link | `external_id` | `vacancy-{sqlite_id}` | 110 rows in slice |
| legacy `source` | `source` | `hh` if HH vacancy id else `legacy_job_search` | §23.8 |
| `company_id` | `company_id` | lookup imported Company UUID | 499 rows ready |
| `title` | `title` | direct | |
| `url` | `url` | direct (HttpUrl) | required |
| description fields | `description` | none in SQLite — null or JSONL merge later | |
| `status` | `status` | enum map §16 | |
| `salary_*`, `cohort`, `relevance`, `notes` | — | **omit** (no target fields) | document in unmapped report |
| `reason/risk/action` | — | **DEFERRED** embedded Assessment §23.1 | not Vacancy columns in target |

### Application

| Legacy field | Target field | Transform | Validation |
|---|---|---|---|
| `id` | `external_id` | `application-{id}` | |
| — | `source` | `legacy_job_search` | §23.8 |
| `vacancy_id` | `vacancy_id` | map legacy → target UUID | |
| `applied_at` | `applied_at` | parse ISO text → timestamptz | |
| `result` | `result` | enum map §16; **NULL stays NULL** | optional outcome |
| `next_action_date` | `next_action_at` | parse date/datetime | |
| `cover_letter_text` | `cover_letter_text` | direct | 93 non-empty |

**Semantics:** legacy `result` is **optional observed outcome**, not required at apply time. **406 NULL results are not corrupt.**

### Person

| Legacy field | Target field | Transform | Validation |
|---|---|---|---|
| `role` | `role` | direct enum | same values |
| `status` | `status` | direct enum | `new`, `dropped` observed |
| `source` | `source` | normalize slug (`company_site` → `legacy_job_search`) | max 64 |
| `id` | `external_id` | `person-{id}` | |
| `hh_vacancy_id` | — | use for Vacancy lookup only | not stored on Person |
| `confidence` | `confidence` | direct | 0–1 |

### DailyMetric

| Legacy field | Target field | Transform | Validation |
|---|---|---|---|
| `date` | `metric_date` | parse date | PK |
| counter columns | same names | direct nullable ints | CHECK ≥ 0 |
| `updated_at` | `updated_at` | parse timestamptz | |

**Early rows (2025-08-29 …):** legacy `settings.search_start_date` = **`2026-06-04`**. All **81** rows import per locked decision **§23.1** (pre-search metrics are valid historical data).

### Hypothesis

| Legacy field | Target field | Transform | Validation |
|---|---|---|---|
| `id` | `external_id` | `hypothesis-{id}` | |
| — | `source` | `legacy_job_search` | |
| `status` | `status` | `active` → `active` | |
| other text fields | direct | | |

### Assessment (embedded columns, 16 rows) — DEFERRED §23.1

Not imported in first slice. No synthetic score, verdict, reason, action, or model metadata. Source SQLite columns remain authoritative until a future slice.

### Assessment (JSONL category A, ≤20 HH ids) — first slice only

| Legacy JSONL | Target field | Transform | Validation |
|---|---|---|---|
| vacancy row | `vacancy_id` | mapped UUID via HH id | parent must exist |
| — | `source` | `legacy_job_search_scoring` | §23.8 |
| HH id | `external_id` | `{hh_vacancy_id}` | latest-only per HH §23.14 |
| `score.score` | `relevance_score` | direct int 0–100 | |
| `score.verdict` | `verdict` | direct | apply/maybe/skip |
| `score.reasons[]` | `reason` | join bullets / newline | required |
| `score.mismatches[]`, `strengths[]` | `risk` or append to `reason` | concat | rich text lossy → WARNING |
| — | `action` | derive from verdict (§16) | required field |
| `score.method` | `model` | `legacy:{method}` | JSONL has no `model` |
| — | `prompt_version` | `legacy_job_search:import` | honest provenance §23.14 |
| `score.scored_at` | `assessed_at` | parse ISO | pick latest per HH |

---

## 16. Enum / status mappings

### Vacancy status (legacy → `VacancyStatus`)

| Legacy | Target | Notes |
|---|---|---|
| `found` | `new` | |
| `viewed` | `reviewing` | |
| `prioritized` | `shortlisted` | |
| `applied` | `reviewing` | apply fact lives in Application row |
| `interview` | `shortlisted` | |
| `reject` | `rejected` | |
| `archived` | `rejected` | |

**MANUAL_REVIEW:** whether `applied`/`interview` should ever be `shortlisted` vs `reviewing` — proposed mapping above is conservative.

### Application result (legacy → `ApplicationResult`)

| Legacy | Target | Notes |
|---|---|---|
| `NULL` | `NULL` | **expected** — no outcome yet |
| `автоответ` | `NULL` | **Owner locked §23.1.8** — not mapped to `reply`; report as legacy anomaly |

### Assessment verdict

JSONL / target: **direct** `apply` | `maybe` | `skip`.

### Derived Assessment `action` (JSONL — no source field)

| Verdict | Proposed `action` |
|---|---|
| `apply` | `apply` |
| `maybe` | `review` |
| `skip` | `skip` |

Finalize in **§23** (Assessment policy).

---

## 17. Identity and idempotency keys

Uses **actual** Core constraints `(source, external_id)` and API idempotency headers.

**Namespace convention (locked §23.6):**

| Case | `source` value |
|---|---|
| Real HH employer / vacancy ID | `hh` |
| Legacy SQLite entities without HH ID | `legacy_job_search` |
| JSONL assessments (cat. A) | `legacy_job_search_scoring` |

| Entity | `source` | `external_id` | Idempotency key |
|---|---|---|---|
| Company (HH) | `hh` | `{employer_id}` | `migrate-{run_id}-company-hh-{employer_id}` |
| Company (no employer) | `legacy_job_search` | `company-{sqlite_id}` | `migrate-{run_id}-company-{sqlite_id}` |
| Vacancy (HH URL) | `hh` | `{hh_vacancy_id}` | `migrate-{run_id}-vacancy-hh-{hh_id}` |
| Vacancy (non-HH in slice) | `legacy_job_search` | `vacancy-{sqlite_id}` | `migrate-{run_id}-vacancy-{sqlite_id}` |
| Application | `legacy_job_search` | `application-{sqlite_id}` | `migrate-{run_id}-application-{sqlite_id}` |
| Person | `legacy_job_search` | `person-{sqlite_id}` | `migrate-{run_id}-person-{sqlite_id}` |
| Hypothesis | `legacy_job_search` | `hypothesis-{sqlite_id}` | `migrate-{run_id}-hypothesis-{sqlite_id}` |
| Assessment (JSONL cat. A, latest) | `legacy_job_search_scoring` | `{hh_vacancy_id}` | `migrate-{run_id}-assessment-hh-{hh_id}` |
| DailyMetric | n/a | `metric_date` PK | `migrate-{run_id}-metric-{date}` |

**Multi-score JSONL:** first slice imports **latest `scored_at` only** per linked HH id; older rows = **DEFERRED HISTORICAL SCORING DATA** (§23.5), not DROP.

---

## 18. Migration dependency order

Based on **target FK requirements** and locked first slice:

```text
Phase 1: Companies (323)
Phase 2: Vacancies (499 with company_id)
Phase 3: Applications (407), People (24)
Phase 4: Assessments — JSONL cat. A latest only (≤20)
Parallel-safe: DailyMetrics (81), Hypotheses (2)
```

**Deferred:** watch-only companies, 12 orphan vacancies, 850 off-DB scores, embedded 16, resume, Content/Telegram, historical score versions.

---

## 19. First supported migration slice — LOCKED

Owner decisions locked in **§23**. Exact first-slice scope:

| Entity | Count | Notes |
|---|---:|---|
| Companies (referenced) | **323** | Parents for funnel + people |
| Vacancies (with `company_id`) | **499** | No synthetic Company for orphans |
| Applications | **407** | `автоответ` → `result=NULL` + report |
| People | **24** | |
| Assessments (JSONL cat. A, latest only) | **≤20** | One per linked HH vacancy |
| Daily metrics | **81** | Includes 17 pre-2026-06-04 rows |
| Hypotheses | **2** | |

**Excluded from first slice (DEFERRED, not DROP):** 1043 watch-only companies; 850 off-DB scored vacancies/assessments; 12 orphan vacancies; 16 embedded incomplete assessments; 139+ historical score lines; resume files; content_logs; telegram JSONL; OSINT raw; secrets/runtime; rebuildable queues.

**Gate intent (preview):** funnel history importable without schema changes; deferred datasets explicitly reported.

---

## 20. Deferred / needs target model

| Dataset | Status | Blocker |
|---|---|---|
| `resume.txt`, `resume_summary.txt` | DEFERRED | CandidateProfile / ResumeVersion (R1) |
| `content_logs`, Telegram artifacts | DEFERRED | Content service not implemented |
| Watch-only companies (1043) | DEFERRED | §23.1 — not first slice |
| JSONL category B (850 HH) | DEFERRED | R2 / PB-02–03 |
| 12 orphan vacancies | DEFERRED | NEEDS_PARENT_ENTITY — no synthetic Company |
| Embedded assessment (16 rows) | DEFERRED | §23.1 — incomplete fields |
| Historical score lines (non-latest) | DEFERRED | §23.5 — scoring history |
| Legacy `settings` | DROP_INTENTIONALLY | Not history |
| Fetch queues, snapshots, secrets | REBUILDABLE / DROP | — |

---

## 21. Decisions — LOCKED in §23

Product-owner decisions required before DATA-00.3 are **locked** in **§23.1–§23.8** and **§23 Migration safety contract**. Section 21 historical questions are superseded.

---

## 22. Next step (historical)

Superseded by **§25**.

---

## 23. Migration safety contract

Binding rules for DATA-00.4+ (dry-run / apply). **No importer code in DATA-00.3.**

### 23.1 Locked owner decisions

| # | Topic | Decision |
|---|---|---|
| 1 | **1043 watch-only companies** | **DEFER** — not in first slice; not DROP; source preserved |
| 2 | **850 off-DB JSONL scores** | **DEFER** — no phantom Vacancies; JSONL remains authoritative; revisit R2/PB-02–03 |
| 3 | **12 vacancies without Company** | **DEFER** — no synthetic/Unknown/Legacy Company for FK |
| 4 | **Pre-search metrics** | **IMPORT all 81** DailyMetric rows |
| 5 | **Multi-score history** | First slice: **latest valid score only**; older rows = **DEFERRED HISTORICAL SCORING DATA** |
| 6 | **16 embedded assessments** | **DEFER** — no default score/verdict |
| 7 | **Content / Telegram** | **DEFER** — NEEDS_TARGET_MODEL; no Content schema for migration |
| 8 | **`автоответ` application result** | Import Application with **`result=NULL`**; anomaly in report; no schema dump field |

### 23.2 First-slice scope (exact)

```text
323 Companies + 499 Vacancies + 407 Applications + 24 People
+ ≤20 Assessments (JSONL cat. A latest) + 81 DailyMetrics + 2 Hypotheses
```

Max planned Core rows (order of magnitude): **~1360** entity inserts (excluding idempotency replay).

### 23.3 Source immutability

**Legacy root:** `/data/Projects/job_search` — **READ-ONLY** for all migration modes.

**Prohibited:**

- SQLite writes, `PRAGMA` that mutates, legacy migrations, cleanup scripts
- Writes to JSONL/artifacts; running legacy app paths that mutate `data/`
- Browser/HH/scoring jobs against archive paths

**Required access:** SQLite URI `file:…?mode=ro`; read-only file opens for artifacts.

**Source fingerprint (mandatory per run):**

| Artifact | Fingerprint |
|---|---|
| `data/job_search.db` | size + mtime + **SHA-256** |
| `data/vacancy_scores.jsonl` | size + SHA-256 |
| `docs/DATA_MIGRATION.md` | git commit SHA at run time (`mapping_version`) |

**Integrity gate:** APPLY forbidden if source fingerprint ≠ dry-run fingerprint.

Record fingerprints in run artifacts under workspace `backups/migration-runs/{run_id}/` (path convention; directory created at DATA-00.4).

### 23.4 Target backup (before APPLY only)

Workspace `make backup` is **not implemented yet** (README / ARCHITECTURE_PLAN). Until added, **mandatory manual backup** before APPLY:

```bash
docker compose exec -T postgres pg_dump -U job_search -d job_search -Fc \
  > backups/migration-runs/{run_id}/target-pre-apply.dump
```

**Backed up:** PostgreSQL database `job_search` in volume `postgres-data` (all Core tables).

**Success criteria:** non-zero dump file; `pg_restore --list` succeeds; operator records path in run manifest.

**Not backed up in first slice:** scoring-state, hh volumes (unchanged by migration).

**Rollback after successful commit:** restore this dump to a clean Postgres volume (documented procedure in DATA-00.6; not per-row undo).

### 23.5 Migration run identity

**Run ID format:** `migrate-YYYYMMDD-HHMMSS-{short_git}` (importer commit short SHA).

Each run produces artifacts:

```text
backups/migration-runs/{run_id}/
  manifest.json          # run metadata
  source-fingerprint.json
  dry-run-report.json    # required before apply
  apply-report.json      # apply only
  target-pre-apply.dump  # apply only
```

**Manifest links:** run_id, mode, mapping_version (DATA_MIGRATION git SHA), importer_version (git SHA), source fingerprint, target backup path (apply), started/finished timestamps.

No new Core DB entity for run tracking.

### 23.6 Dry-run is mandatory

**Mutation** = any INSERT/UPDATE/DELETE/TRUNCATE on target PostgreSQL, Alembic upgrade, or Core API write that persists domain data.

**Dry-run:** read source → transform → validate → resolve parents → emit planned operations report. **Zero target mutation.**

Forbidden as “dry-run”: temporary test rows, rollback-by-hand experiments on production target DB.

**APPLY preconditions:**

1. Successful dry-run for same `{run_id}` scope config
2. Identical source fingerprint
3. Identical `mapping_version` + `importer_version`
4. Target backup completed and verified
5. Preflight validation pass (§23.15)

### 23.7 Idempotency

Identity = Core `(source, external_id)` — **not** target UUID.

| Entity | Re-run behavior |
|---|---|
| Company, Vacancy, Application, Person, Hypothesis, Assessment | If `(source, external_id)` exists and payload **equivalent** → **NO-OP** (report `existing_equivalent`) |
| Same key, different payload | **CONFLICT / FATAL** — stop slice |
| DailyMetric | Same `metric_date` → **VERIFY equivalent**; non-equivalent → **CONFLICT** |
| Idempotency-Key header equivalent | Importer uses deterministic `migrate-{run_id}-…` keys; **re-run with new run_id** must still dedupe via `(source, external_id)` |

No blind upsert. No last-write-wins.

### 23.8 Legacy identity namespace

| `source` | When |
|---|---|
| `hh` | Canonical HH employer_id or HH vacancy_id |
| `legacy_job_search` | SQLite-backed entities without HH external id |
| `legacy_job_search_scoring` | Latest JSONL assessment per HH vacancy (cat. A) |

`external_id` carries sqlite id or HH id — **not** ambiguous `legacy` alone.

Future HH service sync must not collide: HH-native ids use `source=hh`; migration uses `legacy_job_search*` only for non-HH keys.

### 23.9 FK / dependency contract

**Import order (first slice):**

```text
Phase 1: Companies (323)
Phase 2: Vacancies (499)
Phase 3: Applications (407), People (24)
Phase 4: Assessments (≤20, cat. A latest)
Parallel-safe: DailyMetrics (81), Hypotheses (2)
```

If parent not in approved slice → **child skipped with FATAL** (should not occur after preflight).

**Forbidden:** synthetic parent Company; NULL required FK; silent relink to “closest” company.

### 23.10 Transaction boundaries

First slice ≈ **1.3k rows** — fits single PostgreSQL transaction.

**Recommendation:** one **Core SQLAlchemy Session**, one `session.commit()` at end of APPLY for phases 1–4 + metrics + hypotheses.

**On any FATAL in APPLY:** `session.rollback()` — no partial funnel.

DailyMetric/Hypothesis writes in same transaction to avoid half-migrated state.

If importer later exceeds practical lock duration, split only at documented phase boundaries with explicit verification between commits (not needed for first slice).

### 23.11 Target write path (recommendation)

**Chosen:** dedicated **migration adapter** in workspace calling **Core application services** (`create_vacancy`, `create_application`, `create_person`, `create_assessment`, `set_daily_metric`, `create_hypothesis`) via shared SQLAlchemy `Session`.

**Not chosen:**

| Path | Reason |
|---|---|
| HTTP Core API | Harder to hold single transaction; slower; unnecessary network |
| Raw PostgreSQL | Bypasses enum validation, fingerprints, domain invariants |
| Direct ORM bypass everywhere | Duplicates service logic |

**Company-only rows (3 people-parent companies):** use same upsert logic as `create_vacancy` Company branch (insert Company if missing) — **not** a new public API.

Implementation location: future `scripts/migrate_legacy.py` or `services/core` migration CLI module (DATA-00.4 decision).

### 23.12 Insert / update / conflict policy

| Situation | Policy |
|---|---|
| `(source, external_id)` absent | Planned **INSERT** |
| Present, byte-equivalent normalized payload | **NO-OP** |
| Present, different normalized payload | **CONFLICT → FATAL** (stop run) |
| Vacancy status on replay | **NO-OP** if already imported (do not mutate status on re-run unless explicit future rule) |

Historical migration: **never silent UPDATE** of existing non-equivalent records.

### 23.13 Enum / status failure policy

**Complete known mappings:** §16 (Vacancy status, Person role/status, Assessment verdict, Hypothesis status).

**Application result:** only `NULL` or mapped enum values; **`автоответ` → NULL** with `legacy_anomaly` report entry.

**Unknown legacy enum/value:** **FATAL** for that entity; no silent coercion; no default enum.

Preflight must validate 100% of slice rows map to known enums or explicit NULL rules before APPLY.

### 23.14 Assessment migration policy (first slice)

- **Only** JSONL category **A** (HH ids linked to imported Vacancies)
- **One** assessment per HH id: **latest valid** by `scored_at`
- **Exclude:** embedded 16; cat. B (850); historical non-latest score lines
- **Fields:** `relevance_score`, `verdict`, joined `reasons[]`, optional `risk` from mismatches, `action` derived from verdict (§16)
- **`model`:** `legacy:{method}` (honest provenance)
- **`prompt_version`:** `legacy_job_search:import` — marks import provenance, **not** a real historical prompt version
- **`external_id`:** `{hh_vacancy_id}` under `source=legacy_job_search_scoring`

### 23.15 Preflight validation (before APPLY)

All must pass:

- Expected slice counts (323/499/407/24/81/2/≤20)
- Unique `(source, external_id)` per entity type in plan
- All parent UUIDs resolved
- Enum mapping coverage
- Required fields non-empty
- Timestamps parse to UTC
- Assessment score 0–100, verdict valid
- No duplicate HH vacancy mapping ambiguity
- Deferred datasets excluded from write plan
- Source fingerprint match

Failure → APPLY **does not start**.

### 23.16 Error severity

| Severity | When | Action |
|---|---|---|
| **FATAL** | Source fingerprint mismatch; backup failure; duplicate identity ambiguity; missing required parent in slice; unknown required enum; CONFLICT on existing non-equivalent row | Abort run; rollback if mid-APPLY |
| **SKIP_WITH_REPORT** | Row outside first slice (deferred by design); already recorded in deferred inventory | No write; count in report |
| **WARNING** | `автоответ` nulled; lossy merge of reasons/mismatches into Assessment text; nullable field absent | Proceed if preflight OK; must appear in report |

Mapping failures are **never** WARNING-only.

### 23.17 Migration report contract (DATA-00.4+)

Each dry-run / apply produces **JSON** + short **Markdown summary**.

Minimum fields:

- `run_id`, `mode` (`DRY_RUN` | `APPLY`)
- `source_fingerprint`, `mapping_version`, `importer_version`
- `started_at`, `finished_at`, `status`
- Per entity: `source_rows`, `eligible`, `planned_insert`, `existing_equivalent`, `conflict`, `deferred`, `skipped`, `applied`
- `validation_errors[]`, `legacy_anomalies[]` (incl. `автоответ`)
- `deferred_summary` (counts + reasons)
- `target_backup_path` (apply only)

### 23.18 Verification contract (DATA-00.6 preview)

After APPLY:

- Target counts match plan (`applied` totals)
- Every planned `(source, external_id)` exists
- FK samples: application→vacancy, vacancy→company, person→company/vacancy, assessment→vacancy
- No duplicate `(source, external_id)` violations
- Metrics: 81 dates present; hypotheses: 2
- **Absence checks:** zero imported watch-only-only companies beyond 323; zero cat. B assessments; zero orphan vacancies
- Representative record spot-checks (not only counts)

### 23.19 Rollback policy

| Phase | Policy |
|---|---|
| Before commit | SQLAlchemy `rollback()` — empty mutation |
| After successful commit | Restore `target-pre-apply.dump` to Postgres volume |
| Per-row reverse migration | **Not required** |

Failed APPLY mid-transaction → automatic rollback; target unchanged.

### 23.20 Deferred-data guarantee

**DEFERRED ≠ DROPPED.**

| Dataset | Source location | Count | Future milestone |
|---|---|---:|---|
| Watch-only companies | SQLite `companies` | 1043 | Optional later increment |
| Off-DB JSONL vacancies/scores | `vacancy_scores.jsonl` | 850 HH | R2 / PB-02–03 |
| Orphan vacancies | SQLite `vacancies` | 12 | After HH parent recovery |
| Historical score lines | JSONL | 139+ extra lines | R2 scoring history |
| Embedded incomplete assessments | SQLite columns | 16 | MANUAL_REVIEW / future |
| Resume files | `data/resume*.txt` | 2 | R1 CandidateProfile |
| Content / Telegram | SQLite + JSONL | 28 + 29 | Content service |

Legacy source remains authoritative for all deferred data.

---

## 24. DATA-00.3 decisions

| Decision | Outcome |
|---|---|
| Write path | Core application services via migration adapter + single Session |
| Transaction | Single commit for first slice |
| Source namespace | `hh` + `legacy_job_search` + `legacy_job_search_scoring` |
| Dry-run | Mandatory; zero target mutation |
| Backup | `pg_dump` to `backups/migration-runs/{run_id}/` before APPLY |
| Idempotency | `(source, external_id)` equivalence NO-OP; conflict = FATAL |
| Re-run safety | Same data + new run_id → NO-OP on existing equivalents |
| Assessment history | Latest only in slice; rest DEFERRED |
| Embedded assessments | Excluded from slice |

---

## 25. Next step

**PB-DATA-00.5 — Backup + first supported migration APPLY**

Implement target backup + real import per §23.4–§23.19 using the DATA-00.4 dry-run plan.

---

## 26. DATA-00.4 dry-run implementation

| Item | Value |
|---|---|
| **Command** | `make migration-dry-run` |
| **Module** | `scripts/migration/` (`python -m scripts.migration dry-run`) |
| **Runtime** | Core venv (`services/core/.venv`) + `PYTHONPATH=.:services/core/src` |
| **Artifacts** | `backups/migration-runs/{run_id}/` (`source-fingerprint.json`, `dry-run-report.json`, `dry-run-report.md`) |
| **Zero-write guarantee** | Source opened SQLite `mode=ro`; target uses PostgreSQL `BEGIN READ ONLY` + session rollback; row-count before/after guard |
| **Tests** | `tests/test_migration_dry_run.py` (via `make test` / `make unit`) |

### Latest live dry-run (2026-08-22)

| Field | Value |
|---|---|
| **Run ID** | `migrate-20260822-074357-e2d1df7` |
| **Result** | **PASS** |
| **Source DB SHA-256** | `33cd9776dbf141d85d06381108c3f2208c5699b13395f5bc1bd2f65a0ebee983` |
| **JSONL SHA-256** | `e21e18f96dff58c9817a8826c7d477837fa255cf0b9022a48992295c3f3922b2` |
| **Target mutation** | **none** (counts unchanged) |

**Eligible / planned inserts:**

| Entity | Eligible | Planned insert |
|---|---:|---:|
| Companies | 323 | 323 |
| Vacancies | 499 | 499 |
| Applications | 407 | 407 |
| People | 24 | 24 |
| Daily metrics | 81 | 81 |
| Hypotheses | 2 | 2 |
| Assessments | **19** | **19** |

**Assessment note:** JSONL category A contains **20** HH ids linked to SQLite URLs, but **1** score (`134532490`) belongs to orphan vacancy `520` without `company_id` → **DEFERRED** as `orphan_vacancy_linked_score`. First slice imports **19** assessments only.

**Migration sentinels (not historical policy):**

- `prompt_version = legacy_job_search:import`
- missing vacancy URL fallback → company `hh_url` / `site_url` / `https://legacy.job-search.invalid/vacancy/{id}` with report warnings

**Legacy anomaly:** 1× `legacy_result_autoreply` (`application:3`).

**Deferred highlights:** 1043 watch-only companies · 12 orphan vacancies · 850 off-DB scores · 16 embedded assessments · 988 off-DB score lines · 1 historical score line · 1 orphan-linked assessment.

---

## Scoring JSONL breakdown (870 HH vacancy IDs)

| Category | HH ids | Score lines | Description | Mapping status |
|---|---:|---:|---|---|
| **A** Linked to SQLite vacancy | **20** | **21** | HH id exists in DB URL | Assessment **SUPPORTED_NOW** after Vacancy import |
| **B** Off-DB, reconstructable payload | **850** | **988** | JSONL `vacancy` has title + description/URL | **DEFERRED** — R2 / PB-02–03 §23.1 |
| **C** HH id only / insufficient | **0** | **0** | — | — |
| **D** Malformed | **0** | **0** | — | — |

**Multi-score:** 134 HH ids with >1 line; methods: `ollama` 871, `rules` 137, `manual+ollama` 1; verdicts: maybe 570, apply 223, skip 216.

### Embedded assessment vs JSONL (16 rows)

| Check | Result |
|---|---|
| Overlap same HH id in JSONL | **0 / 16** |
| Interpretation | Separate **legacy board column** scoring generation, not duplicate of JSONL |
| Precedence rule | JSONL cat. A only in first slice; embedded 16 **DEFERRED** §23.1 |
| If both existed for same vacancy | would be **MANUAL_REVIEW** — not observed |

---

## Inspection reproducibility (DATA-00.2)

| Check | Result |
|---|---|
| Legacy git changes under `data/` | **None tracked** (`data/*` gitignored) |
| `job_search.db` mtime before/after inspection | **Unchanged:** `2026-07-31 14:21:07 +0300` |
| SQLite opened read-only | Yes (`file:...?mode=ro`) |
| Secrets in this document | **None** (no token values, cover letter text, or chat content) |
| Legacy mutating scripts run | **None** (DATA-00.1 + DATA-00.2) |
| `job_search.db` mtime after DATA-00.2 | **Unchanged:** `2026-07-31 14:21:07 +0300` |

Mapping inspection on **2026-08-22** against Core @ `services/core` models/schemas.
