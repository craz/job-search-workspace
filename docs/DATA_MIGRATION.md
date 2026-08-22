# Job Search Legacy Data Migration

## Status

| Field | Value |
|---|---|
| **Slice** | PB-DATA-00.1 — Legacy inventory |
| **Date** | 2026-08-22 (UTC+3) |
| **Source** | `/data/Projects/job_search` (read-only) |
| **Target** | `/data/Projects/job_search_ref` (Core PostgreSQL) |
| **Source policy** | Read-only inspection only; no writes to source |
| **Next slice** | PB-DATA-00.2 — Source → target mapping |

Prior code inventory (module ownership, not entity counts): `docs/inventory/data.md`, `docs/inventory/migration-map.md`.

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

## 11. Unknowns requiring DATA-00.2 investigation

1. **Scoring merge strategy:** import JSONL scores as Assessments for HH IDs only, create missing Vacancies, or import overlap-only?
2. **Watchlist companies:** migrate all **1366** or only companies referenced by vacancies/people?
3. **Embedded vs JSONL assessment:** how to dedupe 16 column rows vs JSONL for same vacancy?
4. **Target Assessment model** in Core vs legacy split (columns + JSONL rich payload) — mapping status likely `NEEDS_TARGET_MODEL` for full JSONL fields.
5. **Content logs:** verify `draft_path` files exist; Content service stub in target — defer or map to Core?
6. **Settings keys:** which become typed config vs dropped cursors?
7. **Resume/profile:** map files to future CandidateProfile/ResumeVersion (R1) — `NEEDS_TARGET_MODEL`.
8. **12 vacancies without `company_id`:** infer company from text/URL or import with null company?
9. **Daily metrics before `search_start_date`:** include rows from **2025-08-29** or trim to search window?
10. **Legacy status enum** (`viewed`, `reject`, …) → Core `VacancyStatus` mapping validation.

**Observation (non-binding):** SQLite entities **likely map** to Core Vacancy/Company/Application/Person/DailyMetric/Hypothesis; scoring JSONL **likely maps** to Core Assessment with extra payload decisions pending.

---

## 12. Next step

**PB-DATA-00.2 — Source → target mapping**

Produce mapping table per entity with statuses: `SUPPORTED_NOW`, `NEEDS_TARGET_MODEL`, `DROP_INTENTIONALLY`, `MANUAL_REVIEW`.

---

## Inspection reproducibility

| Check | Result |
|---|---|
| Legacy git changes under `data/` | **None tracked** (`data/*` gitignored) |
| `job_search.db` mtime before/after inspection | **Unchanged:** `2026-07-31 14:21:07 +0300` |
| SQLite opened read-only | Yes (`file:...?mode=ro`) |
| Secrets in this document | **None** (no token values, cover letter text, or chat content) |
| Legacy mutating scripts run | **None** |

Inventory queries reproduced via read-only SQLite + file metadata inspection on **2026-08-22**.
