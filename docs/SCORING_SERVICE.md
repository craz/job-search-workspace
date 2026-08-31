# Scoring service — canonical design (R2.3 foundation)

**Status:** R2.3.1–R2.3.3 **COMPLETE**; R2.3.4 FAST E2E + async HTTP **READY FOR OWNER ACCEPTANCE**  
**Aligned with:** Google Doc *Job Search* → PB-03, Roadmap R2, R2 tab  
**ADRs:** [005](adr/005-scoring-service-boundary-and-ownership.md), [006](adr/006-scoring-result-policy-identity.md), [007](adr/007-llm-provider-boundary-ollama.md)

**Design donor (patterns only):** AI Development Control Plane — provider-neutral
request/result contracts, bounded input, honest usage telemetry, deterministic
validation before domain acceptance, fail-closed semantics. **No runtime/package
dependency** on devai or related Git/Cursor/swarm tooling.

---

## 1. Purpose

Score **Vacancies** against the operator’s **scoring-ready candidate context**
using local LLM inference, producing a structured result persisted in Core as
**Assessment** (canonical ScoringResult for Roadmap v1).

R2.3 establishes contracts, ownership, policy identity, provider boundary, and
single-vacancy **fast** scoring E2E (async HTTP). R2.4 adds mass batch + list
prioritization UI. R2.5 adds **detailed** scoring UX in Vacancy expand.

---

## 2. Scope / non-scope

### In scope (R2.3 foundation)

- Hybrid Core `Assessment` extension (ADR-006) — **R2.3.1 COMPLETE**
- Policy-derived verdict; `scoring_identity_hash` uniqueness — **R2.3.1 COMPLETE**
- Scoring-ready context from Core `ResumeVersion` — **R2.3.2 COMPLETE**
- **`GenerationBackend` + Ollama generation** — **R2.3.3 COMPLETE**
- Core `GET /api/v1/vacancies/{id}` — **R2.3.2 COMPLETE**
- Single-vacancy **FAST** scoring E2E + evidence validation — **R2.3.4**
- Async `POST /api/v1/score/fast` (202 Accepted) — **R2.3.4**
- Calibration/benchmark evidence before mass scoring — **R2.3.6** (planned)

### Out of scope

| Area | Slice |
|---|---|
| Batch enqueue + list ranking UI | R2.4 |
| Detailed scoring HTTP implementation | R2.5 (contract may be documented) |
| `EmbeddingBackend` implementation | R2.4+ |
| Deterministic FAIL → verdict override | policy v2+ |
| LLM self-confidence as product signal | not v1 |
| Vector DB | — |
| External/cloud LLM routing | post-R2.3 |
| Mass scoring before calibration evidence | blocked until R2.3.6 |

---

## 3. Product role in UJM

UJM stage 4 — AI-оценка и приоритизация. Scoring is **contextual to Vacancy**,
not a top-level workspace.

---

## 4. Inputs

| Input | Source | Required |
|---|---|---|
| `vacancy_id` + `content_hash` | Core `GET /vacancies/{id}` | yes |
| `profile_version_id` | candidate context | yes |
| `resume_version_id` | Core `ResumeVersion` | yes |
| `hh_resume_external_id` | provenance only (not in identity hash) | yes |
| `ScoringPolicy` | Scoring config | yes |
| `scoring_mode` | `fast` \| `detailed` | yes (`fast` in R2.3.4) |

---

## 5. Candidate context

Assembly (R2.3.2):

1. `GET /api/v1/candidate-context`
2. `GET /api/v1/resume-versions/{id}` (or equivalent content read)
3. **`GET /api/v1/vacancies/{id}`** — **approved**; Scoring must **not** list-all
   and filter client-side.

---

## 6. ScoringPolicy

```json
{
  "policy_id": "default-v1",
  "policy_version": 1,
  "policy_hash": "<sha256 canonical material policy>",
  "verdict_thresholds": { "apply_min": 75, "maybe_min": 50 },
  "mode_configs": {
    "fast": { "template": "fast-v1", "max_tokens": 400 }
  },
  "deterministic_signals": { "enabled": [] }
}
```

### policy_hash semantics

`policy_hash` covers **all material policy behavior**, including:

- threshold values (`apply_min`, `maybe_min`, …)
- scoring rules and mode configs
- **`resolved_template_digest`** — deterministic hash of the **resolved prompt/template
  content actually used** (not path, name, ref, or comments alone)
- result schema expectations
- deterministic weighting/override rules when they exist

Conceptually:

```text
policy_hash = H(
  thresholds,
  scoring rules,
  resolved_template_digest,
  result schema contract,
  deterministic weighting/override semantics
)
```

Computed from canonical serialized policy (stable key order). Comments, formatting,
and file path **must not** change the hash if semantics are identical.

---

## 7. Fast vs detailed

| Mode | R2 slice | Notes |
|---|---|---|
| **fast** | R2.3.4 + R2.4 batch | async HTTP in foundation |
| **detailed** | R2.5 | contract documented; impl deferred |

Separate templates; separate `scoring_mode` in identity hash.

---

## 8. Deterministic signals

Per signal: `PASS` | `FAIL` | `UNKNOWN`. Missing data → **UNKNOWN**.

**R2.3 foundation:** signals may inform LLM context and be stored in JSONB detail.
**FAIL does not override canonical verdict.** No hidden `FAIL → skip` in policy v1.

---

## 9. Embeddings (future)

- Semantic signal / retrieval — **not** verdict.
- **`EmbeddingBackend`** (future) → Ollama `POST /api/embed`.
- **Not implemented in R2.3.3**; must not block foundation.
- No vector DB in R2.3.

---

## 10. ContextRetriever v1

**No arbitrary raw character/token truncation as the primary strategy.**

```text
if normalized ResumeVersion fits context budget:
  → use scoring-relevant normalized snapshot in full
else:
  → deterministic section-aware selection
```

Prefer sections: summary/profile, relevant experience, skills, education when
relevant, scoring-relevant preferences. Extensible for embedding retrieval later.

---

## 11. Provider boundary

See ADR-007.

```text
ScoringOrchestrator (R2.3.4)
  → DeterministicSignalEngine (optional, v1+)
  → ContextRetriever                         # R2.3.2 COMPLETE
  → PromptBuilder(policy, mode)              # R2.3.4 COMPLETE
  → GenerationBackend.generate()             # R2.3.3 COMPLETE
  → domain output/evidence validation        # R2.3.4 COMPLETE
  → PolicyVerdictDeriver(thresholds)
  → Core Assessment write
```

### GenerationBackend (R2.3.3)

Provider-neutral contracts in Scoring:

| Type | Role |
|---|---|
| `GenerationRequest` | prompt, optional system, output schema, model, material generation config, timeout |
| `GenerationResult` | structured payload, provider, resolved model tag, digest, usage, duration |
| `GenerationUsage` | `input_tokens` / `output_tokens` as `int \| None`; `usage_reported` explicit |
| `GenerationBackend` | `generate(request) -> GenerationResult` |

**Usage semantics:** missing token counts are **unknown** (`None`). A provider-confirmed
zero is `0`. Never coerce unknown → zero.

**Privacy (R2.3.3):** success returns normalized in-memory result only. Do not durably
store full prompts, ResumeVersion/Vacancy bodies, secrets, or raw successful provider
responses. Bounded raw failure retention — R2.3.5.

**Ollama adapter:** `POST /api/generate`, non-streaming, structured JSON schema via
`format`, `think: false` for structured generation (reasoning channel disabled),
model resolved from `/api/tags`, digest from tag metadata when available.

**Thinking boundary:** structured output is parsed **only** from the provider final
`response` field. The `thinking`/reasoning channel is never used as structured output,
never persisted, and never exposed in `GenerationResult`.

**Output schema subset (R2.3.3–R2.3.4):** recursive `object` / `array` / `items` /
`properties` / `required` / `additionalProperties: false` with leaf types
`boolean`, `string`, `integer`, `number`. Unsupported JSON Schema keywords
(`$ref`, `allOf`, `anyOf`, `oneOf`, …) → `unsupported_output_schema` before
provider transport.

**Smoke only in R2.3.3:** generic schema `{ok: boolean, label: string}` — not production
vacancy scoring output.

---

## 12. Ollama implementation

| Capability | API | R2.3 |
|---|---|---|
| Generation | `POST /api/generate` | **required** (R2.3.3) |
| Embeddings | `POST /api/embed` | documented only |

`model_fingerprint` uses model tag + digest (when available) + material generation
config hash (temperature, seed if used, num_predict, …).

---

## 13. Assessment hybrid schema (Core — R2.3.1)

**Assessment is the canonical store.** Hybrid persistence:

### Explicit columns (query / identity)

| Column | Type / notes |
|---|---|
| `id` | UUID PK |
| `vacancy_id` | FK |
| `vacancy_content_hash` | string(64) |
| `profile_version_id` | UUID |
| `resume_version_id` | UUID |
| `candidate_context_hash` | string(64) — assembled context after ContextRetriever |
| `scoring_mode` | enum `fast` \| `detailed` |
| `relevance_score` | int 0–100 |
| `verdict` | enum `apply` \| `maybe` \| `skip` (**policy-derived**) |
| `policy_id` | string |
| `policy_version` | int |
| `policy_hash` | string(64) |
| `model_fingerprint` | string(64) |
| `scoring_identity_hash` | string(64), **unique among successful results** |
| `schema_version` | int |
| `assessed_at` | timestamptz |
| `source`, `external_id`, `idempotency_key` | integration (existing) |
| `model` | display name optional (human-readable; fingerprint is identity) |

### JSONB detail (evolving explanation)

Column e.g. `detail` (name TBD in migration):

```json
{
  "reason": "…",
  "risk": "…",
  "action": "…",
  "strengths": ["…"],
  "gaps": ["…"],
  "ambiguities": ["…"],
  "evidence": [
    {
      "claim": "…",
      "source": "vacancy|candidate",
      "section": "experience[0]|skills|description|…",
      "fact": "…"
    }
  ],
  "deterministic_signals": [
    { "signal": "salary", "result": "UNKNOWN", "detail": "…" }
  ],
  "provider_diagnostic": {
    "llm_verdict": "maybe",
    "raw_score_notes": "…"
  }
}
```

**Evidence contract (R2.3.4):** provider output `FastScoringProviderOutput` with
`relevance_score`, explanations, and `evidence[]`. Each `EvidenceItem` has
`kind`, `claim`, `vacancy_refs`, `candidate_refs`.

**Reference grammar:** `vacancy:/json/pointer` and `candidate:/json/pointer`
(RFC 6901). Bare `/pointer` refs in the vacancy/candidate ref arrays are
normalized server-side before validation. Every ref must resolve against the
exact Vacancy/Candidate material blocks sent to the model; invalid paths fail
closed (`invalid_fast_output:evidence_refs`).

Accepted `kind` values: `strength`, `gap`, `fit`, `ambiguity`, `requirement`,
`preference`. Persisted `detail.evidence` stores claim, validated refs, and
bounded `resolved_snippets` — not full prompt or resume bodies.

LLM `action` text is explanatory only; canonical `verdict` is policy-derived.

**Not in canonical v1:** `confidence` as product field.

### Canonical verdict algorithm

After LLM returns `relevance_score` (0–100):

```text
if score >= policy.verdict_thresholds.apply_min:
    verdict = apply
elif score >= policy.verdict_thresholds.maybe_min:
    verdict = maybe
else:
    verdict = skip
```

LLM-returned verdict (if any) → `provider_diagnostic` only.

---

## 14. Scoring identity and model fingerprint

```text
scoring_identity_hash = SHA256_canonical(
  vacancy_content_hash,
  profile_version_id,
  resume_version_id,
  candidate_context_hash,
  policy_hash,
  model_fingerprint,
  scoring_mode
)

model_fingerprint = SHA256_canonical(
  ollama_model_name_or_tag,
  ollama_model_digest | "",
  material_generation_config_hash
)
```

`hh_resume_external_id` — provenance column or JSONB only; **excluded** from identity.

### Current result (no `is_current` flag)

Result is **current** iff `scoring_identity_hash` equals identity computed from
**present** material inputs. Historical Assessments with other hashes remain.

### Successful-result uniqueness

```text
UNIQUE (scoring_identity_hash) WHERE scoring_identity_hash IS NOT NULL
```

Legacy rows with NULL identity coexist. New v1 writes require complete identity.
Do **not** fabricate provenance for historical Assessments.

Same identity + repeat request → reuse existing Assessment; skip Ollama by default.

### Derived current / stale semantics (R2.3.5)

There is **no** persisted `is_current` column. Scoring resolves state per Vacancy:

| `state` | Meaning |
|---|---|
| `never_scored` | No canonical Assessment with complete identity for this Vacancy |
| `current` | A successful Assessment exists whose `scoring_identity_hash` equals the identity computed from **present** material inputs |
| `stale` | A canonical Assessment exists but its stored identity differs from the present identity |

Historical Assessments remain immutable. Stale rows are **not** mutated.

**Stale reason codes** (machine-readable, deterministic when provenance is complete):

`vacancy_changed`, `profile_version_changed`, `resume_version_changed`,
`candidate_context_changed`, `policy_changed`, `model_changed`, `scoring_mode_changed`.

When stored provenance is incomplete or `scoring_identity_hash` is NULL →
`legacy_incomplete_provenance`. Legacy NULL-identity rows are never reused as exact
current v1 results.

**Invalidation matrix:** identity changes when any material component changes
(`vacancy_content_hash`, `profile_version_id`, `resume_version_id`,
`candidate_context_hash`, `policy_hash`, `model_fingerprint`, `scoring_mode`).
Transport host/port/timing, resume PDF artifact path, and provenance-only HH ids
do **not** change identity.

**Re-score semantics:**

- Unchanged canonical identity → reuse existing Assessment; no `GenerationBackend` call.
- Material input change → new identity → new Assessment write; prior Assessment becomes stale.
- Calibration repeats belong to **R2.3.6** evaluation harness, not duplicate canonical writes.

**Resolver:** `resolve_scoring_state(vacancy_id)` returns `current_scoring_identity_hash`,
`reusable_assessment_id` (exact match), `latest_assessment_id`, and `stale_reason_codes`.

Exposed via `GET /api/v1/vacancies/{vacancy_id}/scoring-state` and CLI `resolve-state`.

---

## 15. Persistence ownership

| Artifact | Owner |
|---|---|
| Assessment (structured result) | **Core** |
| Queue, bounded failure diagnostics | **Scoring** `{state_dir}/failures/` |
| ScoringPolicy files | **Scoring** repo config |
| Resume body | **Core** `ResumeVersion` |

Scoring local state is **not** a second canonical resume store.

---

## 16. Raw LLM / prompt retention

| Case | Retention |
|---|---|
| **Success** | Structured result + execution metadata in Core; **full prompt, system prompt, raw provider response, and thinking are not** durably retained |
| **Failed** | Bounded sanitized diagnostic JSON under `{state_dir}/failures/` — excerpt only when necessary; **no** prompt/resume/vacancy bodies |
| **Resume content** | Never duplicated into permanent Scoring state |
| **Secrets** | Never in raw diagnostics |

Bounded policy (R2.3.5): per-file excerpt max **1024 bytes**; HTTP error message max
**500** chars; max **50** files; max total **256 KiB**; TTL **24 h**; startup cleanup
on each job execute. Secrets and control characters stripped.

---

## 17. Execution / job lifecycle (R2.3.4+)

**FAST HTTP path:** in-process `JobStore` (not durable across restart).

After Scoring restart: canonical Assessments remain in Core; identical requests
recompute identity and reuse via `scoring_identity_hash` without old JobStore state.
Old process-local job IDs may disappear.

**In-process single-flight (R2.3.5):** concurrent requests with the same
`scoring_identity_hash` within one Scoring process share one `GenerationBackend`
call. Different identities run independently. Cross-process duplicate suppression
is **not** guaranteed; Core unique constraint remains final authority (idempotent
reuse on race).

| State | Meaning |
|---|---|
| `queued` | accepted, waiting for background worker |
| `processing` | context loaded, Ollama generation in flight (or waiting on single-flight leader) |
| `done` | Assessment id available (new or reused identity) |
| `error` | sanitized `error_code` / `error_message`; optional bounded `diagnostic_id` |

Legacy file `QueueStore` + CLI worker remain for bootstrap; FAST scoring uses the
HTTP job store.

**FAST pipeline:** ContextRetriever → vacancy scoring material → PromptBuilder
(`fast-v1` template) → exact identity lookup → single-flight → `GenerationBackend`
(when needed) → domain validation → Core Assessment.

**Core exact reuse lookup:** `GET /api/v1/assessments?scoring_identity_hash=<64-hex>`
returns at most one canonical successful Assessment (R2.3.5).

**Model alias:** `job-search-scorer-summary:latest` (provisional foundation from
`qwen3.5:9b-q4_K_M`). Provision explicitly:

```bash
ollama create job-search-scorer-summary:latest \
  -f services/scoring/config/Modelfile.job-search-scorer-summary
```

---

## 18. HTTP contract

### `POST /api/v1/score/fast` — **async by default**

**Request:** `{ "vacancy_id": "…" }`

**Response:** `202 Accepted`

```json
{
  "job_id": "…",
  "status": "queued",
  "links": {
    "job": "/api/v1/jobs/{id}",
    "result": "/api/v1/jobs/{id}/result"
  }
}
```

Product HTTP **must not** block on Ollama completion. CLI may offer `--wait` for
diagnostics.

| Method | Path | R2.3 |
|---|---|---|
| GET | `/api/v1/vacancies/{vacancy_id}/scoring-state` | yes (R2.3.5) |
| GET | `/health/ready` | yes |
| POST | `/api/v1/score/fast` | yes (async) |
| GET | `/api/v1/jobs/{id}` | yes |
| GET | `/api/v1/jobs/{id}/result` | yes |
| POST | `/api/v1/jobs/{id}/retry` | yes |
| POST | `/api/v1/score/detailed` | documented; **R2.5 impl** |

---

## 19. Recovery / errors

Stable codes: `ollama_unavailable`, `model_not_found`, `generation_timeout`,
`invalid_structured_json`, `unsupported_output_schema`, `structured_schema_mismatch`,
`provider_http_failure`, `invalid_model_json`, `vacancy_not_found`, `context_not_ready`, `policy_invalid`,
`core_write_failed`, `identity_already_scored`.

---

## 20. Observability

Log: `vacancy_id`, `scoring_identity_hash`, `policy_hash`, `model_fingerprint`,
`duration_ms`, outcome `reused` \| `scored` \| `failed`.

---

## 21. Security / privacy

Resume in memory only during job; no verbatim resume in durable Scoring logs.

---

## 22. Evolution path

```text
R2.3.1  Assessment/policy/identity           COMPLETE
R2.3.2  scoring-ready context               COMPLETE
R2.3.3  GenerationBackend + Ollama          COMPLETE
R2.3.4  FAST E2E + evidence + async HTTP    COMPLETE
R2.3.5  reuse/staleness/single-flight/     COMPLETE
        failure diagnostics
R2.3.6  calibration/benchmark evidence      IN PROGRESS
R2.3.6.1 harness + blind owner dataset      READY FOR OWNER LABELING
R2.3.6.2 benchmark execution + metrics      NOT STARTED
R2.3.6.3 owner qualitative review           PLANNED
R2.3.A  integrated foundation acceptance
R2.4    batch + list priority + signals/embeddings optional
R2.5    detailed mode
R2.6    user decision
```

### R2.3.6 — calibration / benchmark

Before mass R2.4 scoring, collect evidence on human-labeled Vacancy cases:

```text
same versioned Vacancy + ResumeVersion + ScoringPolicy
  → candidate model/prompt/policy combinations
  → human-labeled expected evidence/decision ranges
  → quality + grounding + calibration + cost + duration
  → advisory route/prompt selection (no automatic routing mutation)
```

**Decomposition:**

| Sub-slice | Scope |
|---|---|
| **R2.3.6.1** | Harness + blind owner label dataset (**READY FOR OWNER LABELING**) |
| **R2.3.6.2** | Run benchmark candidates + quantitative evidence |
| **R2.3.6.3** | Owner qualitative review / calibration decision if needed |

**Private data policy:** real ResumeVersion snapshots, Vacancy material, owner labels,
and benchmark outputs live only under `{state_dir}/calibration/<suite_id>/` and are
**gitignored**. Repository contains schemas, harness code, and **synthetic** fixtures only.

**Real HH eligibility (R2.3.6.1):** owner calibration suites use only Vacancies with
verified HeadHunter `resume_suitable` acquisition provenance:

```text
Vacancy.source == "hh"
AND exists completed SearchRun (success|partial)
    with acquisition_kind == resume_suitable
    AND non-error SearchRunItem linking to the Vacancy
AND usable normalized scoring material (title + content_hash)
```

`source=hh` alone is **insufficient**. Synthetic/adversarial cases remain separate
test assets and are never mixed into reported real-world quality metrics.
Prepare fails closed when eligible pool `< target_count`.

**Canonical Assessment isolation:** calibration repetitions are benchmark artifacts.
They do **not** write Core Assessments and do **not** bypass `scoring_identity_hash`
uniqueness.

**Blind labeling:** owner labels `apply` \| `maybe` \| `skip` relative to current
ResumeVersion and search strategy. Labeling UI/CLI must not show existing Assessment
score/verdict, model reason/evidence, or prior benchmark output.

**CLI:**

```bash
job-search-scoring calibration prepare --seed <seed> --target-count 30
job-search-scoring calibration status --suite-id <suite_id>
job-search-scoring calibration label --suite-id <suite_id>
job-search-scoring calibration validate-labels --suite-id <suite_id>
job-search-scoring calibration show-candidate --suite-id <suite_id>
```

**Benchmark repeats:** default 3 per case/variant on frozen material; no Core reuse.
**Metrics:** confusion matrix, macro F1, critical inversions, ranking pairwise accuracy,
repeat flip rate, failure rates, duration/token summaries (usage unknown preserved).
No confidence v1; no automatic production threshold; recommendations advisory-only.

Initial target dataset size may be documented as ~30–50 labeled cases; not a hard
product guarantee. **Smoke proves the path works; calibration supports trusting
ranking quality.**

---

## 23. Known deferred decisions

| Topic | Defer to |
|---|---|
| JSONB column name / legacy column migration | R2.3.1 |
| Legacy NULL v1 columns on historical rows | R2.3.1 migration |
| Exact raw retention byte limits + cleanup job | **R2.3.5** (implemented) |
| Deterministic FAIL → verdict override | policy v2 |
| Calibrated confidence signal | future schema |
| Batch enqueue API | R2.4 |
| `normalize()` legacy removal | **POST-R2.3.A cleanup** |

---

## Appendix A — Inventory summary

| Component | Verdict |
|---|---|
| CLI + queue + scheduler | **KEEP** |
| `work_once` | **ADAPT** |
| `CoreClient` list-all | **ADAPT** → GET-by-id (R2.3.2) |
| `OllamaClient` | **ADAPT** → `OllamaGenerationBackend` (**R2.3.3**) |
| `normalize()` legacy | **REMOVE AFTER R2.3.A** |
| Modelfile `data/resume.txt` sole source | **ADAPT** → Core ResumeVersion |
