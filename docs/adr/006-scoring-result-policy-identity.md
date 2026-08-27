# ADR-006: ScoringResult, ScoringPolicy versioning, and current-result identity

- Status: accepted (R2.3 architecture)
- Date: 2026-08-28

## Context

Scoring must answer: “Does this Vacancy already have a valid **current** score for
this exact inputs?” Re-scoring must be traceable when vacancy content, resume
snapshot, policy, model, or mode changes.

Today Core `Assessment` stores normalized output but lacks explicit policy
identity, scoring mode (fast/detailed), candidate/resume provenance, and a
first-class **current vs historical** distinction. `prompt_version` is a loose
string tied to embedded Modelfile names.

## Decision

### ScoringPolicy (logical artifact)

- **Separate** from LLM model, `CandidateProfile`, and `ResumeVersion`.
- Identified by `policy_id` + monotonic `policy_version` (or content-addressed
  `policy_hash`).
- Changes to rules, prompt contract, weighting/thresholds, or verdict mapping
  **must** change `policy_hash` even if the human-readable `policy_id` stays the
  same.
- Policy body is structured (JSON/YAML in repo or Scoring config dir) — not
  buried only inside free-form prompt text.

### ScoringResult (logical contract)

Canonical machine fields (mapped to Core `Assessment` + extension metadata):

| Field group | Examples |
|---|---|
| Decision | `relevance_score` 0–100, `verdict` ∈ {apply, maybe, skip} |
| Explanation | structured `reason`, optional `risk`, recommended `action` (bounded text) |
| Confidence | optional 0–1 when model supplies calibrated confidence |
| Provenance | `vacancy_id`, `vacancy_content_hash`, `profile_version_id`, `resume_version_id`, `hh_resume_external_id` |
| Policy | `policy_id`, `policy_version`, `policy_hash` |
| Model | `model_id`, `provider` (=ollama v1), `prompt_template_version` |
| Mode | `fast` \| `detailed` |
| Lifecycle | `assessed_at`, `schema_version`, `is_current` (or separate current-pointer) |
| Errors | stable `error_code` + `recovery_kind` when scoring failed |

Free-form LLM prose is **not** the canonical store; only normalized fields pass
validation.

### Current-result identity

A scoring run is **identical** (eligible for skip / idempotent no-op) when all
material inputs match:

```text
identity = H(
  vacancy_content_hash,
  profile_version_id,
  resume_version_id,
  policy_hash,
  model_id,
  scoring_mode
)
```

- Stored as `scoring_identity_hash` on Assessment (or companion table) in R2.3.1.
- **Vacancy UUID stable + `content_hash` changed** → previous results remain
  historical but are **not current**; vacancy is eligible for re-score (technical
  invalidation only — no “vacancy changed” UI in R2.3).
- Idempotent Core writes continue to use integration `idempotency_key`; scoring
  identity is orthogonal and used for “already current?” checks.

### Verdict semantics

- `relevance_score`: integer **0–100** inclusive (higher = better fit).
- `verdict`: derived by policy thresholds from score **and** optional deterministic
  signal gates; LLM may propose verdict but policy validates/overrides mapping.
- Threshold defaults documented in ScoringPolicy v1; adjustable per policy version.

## Consequences

- R2.3.1 extends Core Assessment (or adds `assessment_provenance` JSONB) — migration
  required before R2.4 UI.
- Re-score creates new Assessment row; marking prior rows non-current is explicit.
- Bootstrap worker `normalize()` legacy schema branch is removed after R2.3.3.
