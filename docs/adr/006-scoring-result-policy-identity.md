# ADR-006: ScoringResult, ScoringPolicy versioning, and current-result identity

- Status: accepted (R2.3 architecture, owner review corrections 2026-08-28)
- Date: 2026-08-28

## Context

Scoring must answer: “Does this Vacancy already have a valid **current** score for
this exact material context?” Re-scoring must be traceable when vacancy content,
resume snapshot, policy, model fingerprint, or mode changes.

Today Core `Assessment` stores normalized output but lacks explicit policy identity,
scoring mode, resume/profile provenance, `scoring_identity_hash`, and
`model_fingerprint`. `prompt_version` is a loose string tied to embedded Modelfile
names. Verdict may be implied from LLM output — **not acceptable** for canonical
product semantics.

## Decision

### Assessment persistence (hybrid — Core)

**Assessment remains the canonical Core entity** for Roadmap v1. No separate
ScoringResult store.

Use **hybrid persistence**:

- **Explicit columns** for query-critical / identity-critical fields.
- **JSONB** for structured, versioned explanation detail.

Minimum columns (names may follow Core conventions):

| Column | Role |
|---|---|
| `vacancy_id` | FK (existing) |
| `vacancy_content_hash` | material vacancy input at score time |
| `profile_version_id` | candidate profile version |
| `resume_version_id` | scored resume snapshot |
| `scoring_mode` | `fast` \| `detailed` |
| `relevance_score` | 0–100 (existing) |
| `verdict` | `apply` \| `maybe` \| `skip` (policy-derived) |
| `policy_id` | human-stable policy name |
| `policy_version` | monotonic int |
| `policy_hash` | content-addressed policy identity |
| `model_fingerprint` | material inference identity (see below) |
| `scoring_identity_hash` | exact-context identity |
| `schema_version` | Assessment detail schema version |
| `assessed_at` | score timestamp (existing) |
| `source`, `external_id`, `idempotency_key` | integration fields (existing) |

JSONB detail (e.g. `detail` or `explanation_json`) holds evolving fields:

- `reason`, `risk`, `action`
- `strengths`, `gaps`
- `deterministic_signals` (when present)
- optional `provider_diagnostic` (e.g. LLM-returned verdict — **not canonical**)
- other versioned explanation fields

Legacy top-level `reason` / `risk` / `action` columns may remain during migration
or move into JSONB in R2.3.1 — implementation chooses least-breaking path.

### ScoringPolicy

- **Separate** from LLM model, `CandidateProfile`, and `ResumeVersion`.
- `policy_id` + `policy_version` + **`policy_hash`**.
- **`policy_hash`** is computed from **canonical serialized material policy**:
  threshold values, scoring rules, prompt/template contract references,
  result schema expectations, and (when added) deterministic weighting/override
  rules. Formatting, comments, and file path **must not** change `policy_hash`
  if semantic policy is identical.
- Policy body is structured (JSON/YAML in Scoring config) — not buried only in
  free-form prompt text.

### Canonical verdict (policy-derived, not LLM)

The LLM produces:

- `relevance_score` (0–100)
- structured explanation fields

**Canonical stored `verdict` is derived only by ScoringPolicy thresholds:**

```text
if relevance_score >= apply_min  → apply
elif relevance_score >= maybe_min → maybe
else                              → skip
```

Thresholds live in ScoringPolicy, not hardcoded in orchestration.

If the provider returns its own verdict, it may be stored only under
`provider_diagnostic` in JSONB — **never** as canonical `verdict`.

**Guarantee:** same `relevance_score` + same `policy_hash` → same `verdict`.

**R2.3 foundation:** deterministic signal `FAIL` does **not** override verdict.
No hidden `FAIL → skip`. Override/weighting semantics are explicit policy v2+.

**Confidence:** generic LLM self-confidence is **not** canonical in v1. May be
parsed into `provider_diagnostic` if returned; not used for ranking or decision.

### Scoring identity (exact context)

```text
scoring_identity_hash = H(
  vacancy_content_hash,
  profile_version_id,
  resume_version_id,
  policy_hash,
  model_fingerprint,
  scoring_mode
)
```

- `hh_resume_external_id` is **provenance only** — **not** part of identity when
  `resume_version_id` identifies the scored content.
- If future material versioned inputs are added, identity evolves with explicit
  `schema_version` / ADR amendment.

### Model fingerprint

Do not rely on mutable model name/tag alone.

```text
model_fingerprint = H(
  ollama_model_name_or_tag,
  ollama_model_digest,          # when available from Ollama show/inspect
  material_generation_config      # canonical hash of temperature, seed (if used),
)                                 # num_predict, and other context-relevant options
```

Same tag + different digest → different fingerprint → eligible new score.
Incidental runtime metadata is excluded from the hash.

### Current result and Core idempotency

**Do not use mutable `is_current=true` as the primary mechanism.**

A result is **current** when its `scoring_identity_hash` equals the identity
computed from **present** material inputs (vacancy hash, resume version, policy,
model fingerprint, mode). Historical rows with older identities remain.

**Successful-result uniqueness (Core):**

- Same `scoring_identity_hash` → **at most one canonical successful Assessment**
  (unique partial index or equivalent invariant).
- Repeat request with identical context → **return/reuse** existing result; **do
  not** call Ollama by default; **do not** create duplicate Assessment.
- HTTP `Idempotency-Key` / job UUID handles **transport retry** only — orthogonal
  to `scoring_identity_hash`.

Failed jobs may retry without creating a successful duplicate.

### Re-score / invalidation

When material inputs change (e.g. vacancy `content_hash`, new `resume_version_id`,
`policy_hash`, `model_fingerprint`), prior Assessments remain historical; the
vacancy is eligible for a new score. No “vacancy changed” UI in R2.3.

## Consequences

- R2.3.1 Core migration: hybrid Assessment columns + JSONB detail + unique
  successful `scoring_identity_hash`.
- Scoring orchestration must compute policy verdict **after** LLM score parse.
- Bootstrap `normalize()` legacy compatibility: **REMOVE AFTER / AS PART OF
  POST-R2.3.A CLEANUP** — not before R2.3.A passes.
