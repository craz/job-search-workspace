# Scoring service — canonical design (R2.3 foundation)

**Status:** architecture / decomposition — **READY FOR OWNER ACCEPTANCE** (impl NOT STARTED)  
**Aligned with:** Google Doc *Job Search* → PB-03, Roadmap R2, R2 tab  
**ADRs:** [005](adr/005-scoring-service-boundary-and-ownership.md), [006](adr/006-scoring-result-policy-identity.md), [007](adr/007-llm-provider-boundary-ollama.md)

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

- Hybrid Core `Assessment` extension (ADR-006)
- Policy-derived verdict; `scoring_identity_hash` uniqueness
- `GenerationBackend` + Ollama generation (R2.3.3)
- Context assembly from Core `ResumeVersion`
- Core `GET /api/v1/vacancies/{id}` (approved R2.3.2 prerequisite)
- Async `POST /api/v1/score/fast` (202 Accepted)
- Queue/worker reuse where sound

### Out of scope

| Area | Slice |
|---|---|
| Batch enqueue + list ranking UI | R2.4 |
| Detailed scoring HTTP implementation | R2.5 (contract may be documented) |
| `EmbeddingBackend` implementation | R2.4+ |
| Deterministic FAIL → verdict override | policy v2+ |
| LLM self-confidence as product signal | not v1 |
| Vector DB | — |

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
ScoringOrchestrator
  → DeterministicSignalEngine (optional, v1+)
  → ContextRetriever
  → PromptBuilder(policy, mode)          # prompt built in memory; not durably stored
  → GenerationBackend.generate_structured()
  → parse relevance_score + explanation
  → PolicyVerdictDeriver(thresholds)     # canonical verdict
  → Core Assessment write
```

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
  "deterministic_signals": [
    { "signal": "salary", "result": "UNKNOWN", "detail": "…" }
  ],
  "provider_diagnostic": {
    "llm_verdict": "maybe",
    "raw_score_notes": "…"
  }
}
```

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

---

## 15. Persistence ownership

| Artifact | Owner |
|---|---|
| Assessment (structured result) | **Core** |
| Queue, bounded raw diagnostics | **Scoring** `scoring-state` |
| ScoringPolicy files | **Scoring** repo config |
| Resume body | **Core** `ResumeVersion` |

Scoring local state is **not** a second canonical resume store.

---

## 16. Raw LLM / prompt retention

| Case | Retention |
|---|---|
| **Success** | Structured result + execution metadata in Core; **full prompt not** retained as durable product data |
| **Failed** (`invalid_model_json`, etc.) | Bounded raw response **excerpt** in `scoring-state/raw/` for debugging |
| **Resume content** | Never duplicated into permanent Scoring state |
| **Secrets** | Never in raw diagnostics |

Bounded policy (R2.3.5 implements cleanup): max size per raw file, TTL or ring
buffer for failed-job artifacts. Exact limits in implementation.

---

## 17. Execution / job lifecycle

Reuse `QueueStore` + scheduler. Job record includes `vacancy_id`, `mode`,
`policy_hash`, `scoring_identity_hash`, `resume_version_id`.

---

## 18. HTTP contract

### `POST /api/v1/score/fast` — **async by default**

**Request:** `{ "vacancy_id": "…" }`

**Response:** `202 Accepted`

```json
{
  "job_id": "…",
  "status": "pending",
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
| GET | `/health/ready` | yes |
| POST | `/api/v1/score/fast` | yes (async) |
| GET | `/api/v1/jobs/{id}` | yes |
| GET | `/api/v1/jobs/{id}/result` | yes |
| POST | `/api/v1/jobs/{id}/retry` | yes |
| POST | `/api/v1/score/detailed` | documented; **R2.5 impl** |

---

## 19. Recovery / errors

Stable codes: `ollama_unavailable`, `invalid_model_json`, `vacancy_not_found`,
`context_not_ready`, `policy_invalid`, `core_write_failed`, `identity_already_scored`.

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
R2.3  foundation (fast async, hybrid Assessment, policy verdict)
R2.4  batch + list priority + signals/embeddings optional
R2.5  detailed mode
R2.6  user decision
```

---

## 23. Known deferred decisions

| Topic | Defer to |
|---|---|
| JSONB column name / legacy column migration | R2.3.1 |
| Legacy NULL v1 columns on historical rows | R2.3.1 migration |
| Exact raw retention byte limits + cleanup job | R2.3.5 |
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
| `OllamaClient` | **ADAPT** → `OllamaGenerationBackend` |
| `normalize()` legacy | **REMOVE AFTER R2.3.A** |
| Modelfile `data/resume.txt` sole source | **ADAPT** → Core ResumeVersion |
