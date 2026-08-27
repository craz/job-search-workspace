# Scoring service — canonical design (R2.3 foundation)

**Status:** architecture / decomposition (R2.3) — **implementation NOT STARTED**  
**Aligned with:** Google Doc *Job Search* → PB-03, Roadmap R2, R2 tab  
**ADRs:** [005](adr/005-scoring-service-boundary-and-ownership.md), [006](adr/006-scoring-result-policy-identity.md), [007](adr/007-llm-provider-boundary-ollama.md)

---

## 1. Purpose

Score **Vacancies** against the operator’s **scoring-ready candidate context**
using local LLM inference, producing a structured **ScoringResult** persisted in
Core as **Assessment**.

R2.3 establishes contracts, ownership, policy identity, provider boundary, and
single-vacancy fast scoring E2E. R2.4 adds mass batch + list prioritization UI.
R2.5 adds detailed scoring UX in Vacancy expand.

---

## 2. Scope / non-scope

### In scope (R2.3 foundation)

- Architecture, contracts, policy/result identity, idempotency rules
- `LlmBackend` + Ollama implementation design
- Context assembly from Core (`ResumeVersion` content — not identifier-only)
- Reuse/adapt JSON file queue + worker where sound
- Minimal HTTP product surface for score-one / job status
- Extension plan for Core `Assessment` provenance fields

### Out of scope (later slices)

| Area | Slice |
|---|---|
| Vacancy list ranking UI, batch enqueue UX | R2.4 |
| Detailed scoring expand UX | R2.5 |
| User decision (PB-04) | R2.6 |
| Auto-apply, HH writes | — |
| OSINT | R3 |
| Embeddings implementation, vector DB | R2.4+ signals (interface only in R2.3) |
| Cloud LLMs, fine-tuning | — |

---

## 3. Product role in UJM

UJM stage 4 — **AI-оценка и приоритизация**:

```text
Active HH resume → suitable vacancies ingested (R2.2)
  → Scoring evaluates each Vacancy vs ResumeVersion
  → score + verdict in Vacancy row (R2.4)
  → operator reviews details / decides (R2.5–R2.6)
```

Scoring is **not** a top-level Web workspace. Results are **contextual to Vacancy**.

---

## 4. Inputs

| Input | Source | Required |
|---|---|---|
| `vacancy_id` | Core | yes |
| Vacancy canonical fields + `content_hash` | Core `Vacancy` | yes |
| `profile_version_id` | Core candidate context | yes |
| `resume_version_id` | Core `ResumeVersion` snapshot | yes |
| `hh_resume_external_id` | Core `ActiveHhResumeLink` | yes (provenance) |
| `ScoringPolicy` | Scoring config (versioned) | yes |
| `scoring_mode` | `fast` \| `detailed` | yes |
| Deterministic signal config | ScoringPolicy | optional v1 |

**Not sufficient:** R1.5 identifier-only `ProfileVersion` without `ResumeVersion`
body (R2.1 resolved this).

---

## 5. Candidate context

**Scoring-ready context** =

```text
CandidateProfile
  → ProfileVersion (label, id)
  → ActiveHhResumeLink (external_id, title, status)
  → ResumeVersion (schema_version, content JSONB, content_hash, captured_at)
```

Assembly:

1. `GET /api/v1/candidate-context` (existing Web/Core contract)
2. `GET /api/v1/resume-versions/{id}` or embedded content endpoint (R2.3.2 —
   add Core read if missing)
3. `GET /api/v1/vacancies/{id}` (R2.3.2 — add Core read-by-id; today Scoring
   list-filters client-side — **ADAPT**)

`ContextRetriever` (§10) selects **relevant slices** of resume content for the
vacancy; v1 may pass summary + top sections; must not assume full dump forever.

---

## 6. ScoringPolicy

Logical versioned artifact:

```json
{
  "policy_id": "default-v1",
  "policy_version": 1,
  "policy_hash": "<sha256 of canonical policy body>",
  "mode_configs": {
    "fast": { "max_tokens": 400, "template": "fast-v1" },
    "detailed": { "max_tokens": 1200, "template": "detailed-v1" }
  },
  "verdict_thresholds": { "apply_min": 75, "maybe_min": 50 },
  "deterministic_signals": { "enabled": ["salary", "location", "experience"] }
}
```

- **policy_hash** changes when rules/thresholds/templates change — independent of
  Ollama model tag.
- `prompt_template_version` references structured templates on disk, not inline
  prose in policy file.

---

## 7. Fast vs detailed

| Mode | Use | Prompt depth | When |
|---|---|---|---|
| **fast** | Rank many vacancies cheaply | Short reason, compact fields | R2.4 batch, default queue |
| **detailed** | Operator opened one Vacancy | Richer explanation, risks, gaps | R2.5 on-demand |

Separate templates and `scoring_mode` in identity hash. **Do not** merge into one
mega-prompt/API.

---

## 8. Deterministic signals

Pre-LLM **signals** (extensible):

| Signal | Example output |
|---|---|
| salary compatibility | PASS / FAIL / UNKNOWN |
| location / work format | PASS / FAIL / UNKNOWN |
| experience mismatch | PASS / FAIL / UNKNOWN |
| required skills presence | PASS / FAIL / UNKNOWN |
| role title mismatch | PASS / FAIL / UNKNOWN |

Contract per signal:

```json
{ "signal": "salary", "result": "UNKNOWN", "detail": "vacancy has no salary" }
```

Rules:

- **UNKNOWN** when data missing — never silent `FAIL`.
- Signals inform LLM context and may **bound** verdict; no hard auto-skip in R2.3
  unless policy explicitly maps FAIL+confidence (deferred).

---

## 9. Embeddings semantics

- **Semantic signal**, not verdict.
- `LlmBackend.embed()` → vectors for vacancy text and resume sections.
- Similarity supports retrieval ranking — **not** stored as final score.
- Storage: in-memory or PostgreSQL-compatible later; **no vector DB** in R2.3.
- `/api/embed` architected; implementation optional in first foundation slice.

---

## 10. ContextRetriever

```python
class ContextRetriever(Protocol):
    def select(self, *, vacancy: VacancyRead, resume: ResumeVersionRead, mode: ScoringMode) -> CandidateContextSlice: ...
```

v1: truncate + section allowlist from `ResumeVersion.content`.  
Later: embedding-based section pick, keyword overlap, deterministic signal hints.

---

## 11. LLM / provider boundary

See ADR-007.

```text
ScoringOrchestrator
  → DeterministicSignalEngine (optional)
  → ContextRetriever
  → PromptBuilder(policy, mode)
  → LlmBackend.generate_structured()
  → ScoringResultValidator
  → Core Assessment write
```

---

## 12. Ollama implementation

| API | Use |
|---|---|
| `POST /api/generate` | fast + detailed structured JSON |
| `POST /api/embed` | future semantic retrieval |

- Host: `127.0.0.1:11434` via Scoring **host network** (compose).
- Modelfile build/verify CLI **retained** but resume moves from static `data/` to
  Core-sourced context in prompts (ADAPT `models.py`).
- Default model: operator-configured (`JOB_SEARCH_SCORING_MODEL`).

---

## 13. ScoringResult schema

`schema_version`: **1**

```json
{
  "schema_version": 1,
  "relevance_score": 72,
  "verdict": "maybe",
  "reason": "…",
  "risk": "…",
  "action": "Review risks manually",
  "confidence": 0.81,
  "structured": {
    "strengths": ["…"],
    "gaps": ["…"],
    "deterministic_signals": []
  },
  "provenance": {
    "vacancy_id": "…",
    "vacancy_content_hash": "…",
    "profile_version_id": "…",
    "resume_version_id": "…",
    "hh_resume_external_id": "…"
  },
  "policy": {
    "policy_id": "default-v1",
    "policy_version": 1,
    "policy_hash": "…"
  },
  "model": {
    "provider": "ollama",
    "model_id": "job-search-scorer-summary:latest"
  },
  "mode": "fast",
  "assessed_at": "2026-08-28T00:00:00Z",
  "scoring_identity_hash": "…"
}
```

Mapped to Core `AssessmentCreate` + extension columns for provenance / `is_current`.

---

## 14. Persistence ownership

| Artifact | Owner |
|---|---|
| Assessment / ScoringResult (normalized) | **Core** PostgreSQL |
| Queue jobs, leases, raw LLM JSON | **Scoring** `scoring-state` volume |
| ScoringPolicy files | **Scoring** repo config (versioned in git) |
| Resume body | **Core** `ResumeVersion` (not Scoring `data/`) |

---

## 15. Idempotency / current-result identity

See ADR-006.

Before enqueue/score:

1. Load vacancy `content_hash` + context version ids + active `policy_hash` + mode.
2. Compute `scoring_identity_hash`.
3. If Core reports matching **current** Assessment → return cached (no Ollama).

Core write:

- `Idempotency-Key`: job UUID (retry-safe)
- `scoring_identity_hash`: logical dedupe across runs

---

## 16. Re-score / invalidation

| Event | Behavior |
|---|---|
| Same identity | Skip (idempotent) |
| Vacancy `content_hash` changed | prior Assessment → `is_current=false`; eligible re-score |
| New `ResumeVersion` for active resume | re-score eligible |
| `policy_hash` changed | re-score eligible |
| Model change (material) | re-score eligible |

No Web badge “vacancy changed” in R2.3 — technical only.

---

## 17. Execution / job lifecycle

**Reuse** `QueueStore` + `scheduler.run` (KEEP):

| Status | Meaning |
|---|---|
| `pending` | queued |
| `running` | worker lease held |
| `done` | Assessment written |
| `failed` | terminal error |
| `cancelled` | operator cancelled pending |

Job record extensions (R2.3.5):

```json
{
  "vacancy_id": "…",
  "mode": "fast",
  "policy_hash": "…",
  "scoring_identity_hash": "…",
  "resume_version_id": "…"
}
```

Lease recovery, retry backoff — **existing behavior retained**.

---

## 18. HTTP contract (target)

Version prefix: `/api/v1` (Scoring service — new in R2.3.4).

| Method | Path | Purpose |
|---|---|---|
| GET | `/health/ready` | process + Ollama reachability + Core reachability |
| POST | `/api/v1/score/fast` | `{ "vacancy_id": "…" }` → enqueue or sync score |
| POST | `/api/v1/score/detailed` | same, `mode=detailed` |
| GET | `/api/v1/jobs/{id}` | status + metadata |
| GET | `/api/v1/jobs/{id}/result` | ScoringResult summary |
| POST | `/api/v1/jobs/{id}/retry` | re-queue failed job |

CLI (`job-search-scoring`) remains for operator diagnostics and scheduler `run`.

Web will proxy Scoring HTTP in R2.4 (same pattern as HH/OSINT).

---

## 19. Recovery / errors

| code | recovery.kind | Meaning |
|---|---|---|
| `ollama_unavailable` | `provider_unavailable` | host Ollama down |
| `invalid_model_json` | `provider_response_invalid` | non-JSON / schema fail |
| `vacancy_not_found` | `input_missing` | Core 404 |
| `context_not_ready` | `context_incomplete` | no ResumeVersion / stale link |
| `policy_invalid` | `configuration_error` | bad policy file |
| `core_write_failed` | `downstream_unavailable` | retryable if 5xx |

Never classify local misconfiguration as “HH outage” pattern (learned from R2.2.5
egress hardening).

---

## 20. Observability

Job + structured logs (no enterprise tracing):

- vacancy_id, mode, policy_hash, model_id
- resume_version_id, vacancy_content_hash
- duration_ms, attempt, error_code
- outcome: skipped_idempotent | scored | failed

`/health/ready` returns `{ ollama: ok|degraded, core: ok|degraded }`.

---

## 21. Security / privacy / local-first

- Single-user trusted local operator; loopback exposure only.
- Resume content flows Core → Scoring in memory; not logged verbatim.
- Raw LLM responses in `scoring-state/raw/` — private volume, not in git.
- No resume/contacts in prompts from unvalidated sources.

---

## 22. Evolution path

```text
R2.3  foundation: contracts, policy, Ollama backend, context from Core, 1-vacancy fast E2E
R2.4  batch enqueue, list prioritization, deterministic signals v1, optional embed retrieval
R2.5  detailed mode UX in Vacancy expand
R2.6  user decision separate from verdict
```

---

## 23. Known deferred decisions

| Topic | Defer to |
|---|---|
| Assessment table shape vs JSONB provenance blob | R2.3.1 implementation |
| Sync vs async default for `POST /score/fast` | R2.3.4 |
| Batch enqueue API shape | R2.4 |
| Verdict override when deterministic FAIL | policy v2 |
| Web proxy auth for Scoring | R2.4 (trusted local, same as Core) |
| Remove bootstrap `data/resume.txt` path | R2.3.2 after Core context wired |
| GET `/api/v1/vacancies/{id}` in Core | R2.3.2 |

---

## Appendix A — Current inventory (2026-08-28)

| Component | Verdict | Notes |
|---|---|---|
| CLI + JSON envelope | **KEEP** | `cli.py` |
| `work_once` pipeline | **ADAPT** | wire context + policy + identity |
| `QueueStore` + scheduler | **KEEP** | `queue.py`, `scheduler.py` |
| `CoreClient` list-all | **ADAPT** | needs GET-by-id |
| `build_vacancy_message` field names | **ADAPT** | align `VacancyRead` |
| `OllamaClient` | **ADAPT** → `OllamaBackend` | ADR-007 |
| Modelfile resume embed | **ADAPT** | move to Core-sourced context |
| `normalize()` dual schema | **REMOVE LATER** | after unified ScoringResult |
| Static capabilities doc | **REMOVE LATER** | stale scaffold text |
| `safe-scaffold.md` | **REMOVE LATER** | superseded |
| No HTTP API | **ADAPT** | add minimal `/api/v1` in R2.3.4 |
| No batch enqueue | **ADAPT** | R2.4 |

Tests today: unit (worker, queue, scheduler, clients, models), contract CLI,
integration queue persistence, BDD pipeline features.
