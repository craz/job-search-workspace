# ADR-007: Provider-independent generation boundary with Ollama (Roadmap v1)

- Status: accepted (R2.3 architecture, owner review corrections 2026-08-28)
- Date: 2026-08-28

## Context

Scoring today calls Ollama `/api/generate` directly from `OllamaClient`. Roadmap
v1 requires **local Ollama only**, but transport details must not spread through
orchestration, signal layers, or tests. R2.3 foundation requires **generation**
only; embeddings are a future capability and must not block R2.3.3.

## Decision

1. Introduce **capability-separated provider protocols** (names illustrative):
   - **`GenerationBackend`**: `generate_structured(request) -> GenerationResult`
   - **`EmbeddingBackend`** (future): `embed(texts) -> list[vector]` — **not
     required in R2.3 implementation**
2. **`OllamaGenerationBackend`** is the sole Roadmap v1 generation implementation:
   - `POST /api/generate` with JSON schema / `format: json`
3. **Future `OllamaEmbeddingBackend`** (R2.4+ when needed):
   - `POST /api/embed` — documented now, **not implemented in R2.3.3**
4. Orchestration depends on **`GenerationBackend`**, not `urllib` + Ollama URLs.
5. **No cloud LLM providers** in scope; adding one later requires new ADR.
6. Model lifecycle (`build` / `inspect` / `verify` Modelfile) remains Ollama-specific
   CLI tooling; `inspect`/`show` output feeds **`model_fingerprint`** (ADR-006).

## Consequences

- R2.3.3 is **not blocked** on embedding functionality.
- Unit tests mock `GenerationBackend`; integration tests may hit host Ollama optionally.
- Embedding-based retrieval added later via `EmbeddingBackend` without rewriting
  fast scoring orchestration.
- Scoring container keeps **host network** to reach `127.0.0.1:11434`.
- No vector DB in R2.3.
