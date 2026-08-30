# ADR-007: Provider-independent generation boundary with Ollama (Roadmap v1)

- Status: accepted (R2.3 architecture; R2.3.3 implementation addendum 2026-08-31)
- Date: 2026-08-28

## Context

Scoring today calls Ollama `/api/generate` directly from `OllamaClient`. Roadmap
v1 requires **local Ollama only**, but transport details must not spread through
orchestration, signal layers, or tests. R2.3 foundation requires **generation**
only; embeddings are a future capability and must not block R2.3.3.

**Design donor (2026-08-31):** the owner's separate *AI Development Control Plane*
project informs generic patterns (provider-neutral contracts, bounded input, honest
usage telemetry, deterministic validation before acceptance, fail-closed behavior,
calibration-before-mass-routing). Job Search **must not** depend on devai package,
Git worktrees, Cursor/Codex executors, swarm runtime, or external provider routing.

## Decision

1. Introduce **capability-separated provider protocols**:
   - **`GenerationBackend`**: `generate(request) -> GenerationResult` (**R2.3.3**)
   - **`EmbeddingBackend`** (future): `embed(texts) -> list[vector]` — **not
     required in R2.3 implementation**
2. **`OllamaGenerationBackend`** is the sole Roadmap v1 generation implementation:
   - `POST /api/generate` with JSON schema / structured `format`
   - `think: false` for structured generation when supported by installed Ollama
   - structured JSON parsed **only** from final `response`; `thinking` is never used
   - model tag + digest resolved from `/api/tags` when available
   - non-streaming for foundation slice
3. **Future `OllamaEmbeddingBackend`** (R2.4+ when needed):
   - `POST /api/embed` — documented now, **not implemented in R2.3.3**
4. Orchestration depends on **`GenerationBackend`**, not `urllib` + Ollama URLs.
5. **No cloud LLM providers** in R2.3.3; adding one later requires new ADR.
6. Model lifecycle (`build` / `inspect` / `verify` Modelfile) remains Ollama-specific
   CLI tooling; tag/digest output feeds **`model_fingerprint`** (ADR-006).
7. **Usage telemetry:** missing token counts are unknown (`None`); never coerce to zero.
8. **Success privacy:** do not durably persist full prompts or raw successful responses.
9. **R2.3.4** adds domain output/evidence validation; **R2.3.6** adds calibration
   evidence before mass R2.4 scoring.

## Consequences

- R2.3.3 is **not blocked** on embedding functionality.
- Unit tests mock `GenerationBackend`; integration tests may hit host Ollama optionally.
- Embedding-based retrieval added later via `EmbeddingBackend` without rewriting
  fast scoring orchestration.
- Scoring container keeps **host network** to reach `127.0.0.1:11434`.
- No vector DB in R2.3.
- Legacy `OllamaClient` may remain for bootstrap worker until R2.3.4 migration.
