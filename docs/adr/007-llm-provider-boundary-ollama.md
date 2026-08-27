# ADR-007: Provider-independent LLM boundary with Ollama (Roadmap v1)

- Status: accepted (R2.3 architecture)
- Date: 2026-08-28

## Context

Scoring today calls Ollama `/api/generate` directly from `OllamaClient`. Roadmap
v1 requires **local Ollama only** (`/api/generate`, `/api/embed`), but transport
details must not spread through orchestration, signal layers, or tests.

## Decision

1. Introduce **`LlmBackend` protocol** (or abstract base) in Scoring with:
   - `generate_structured(request) -> LlmGenerateResult`
   - `embed(texts) -> list[vector]` (optional in R2.3 foundation; required on
     interface for R2.4+ semantic signals)
2. **`OllamaBackend`** is the sole Roadmap v1 implementation:
   - generate → `POST /api/generate` with JSON schema / `format: json`
   - embed → `POST /api/embed`
3. Orchestration depends on **`LlmBackend`**, not `urllib` + Ollama URLs.
4. **No cloud LLM providers** in scope; adding one later requires new ADR.
5. Model lifecycle (`build` / `inspect` / `verify` Modelfile) remains Ollama-specific
   CLI tooling but feeds configuration into `OllamaBackend`.

## Consequences

- Unit tests mock `LlmBackend`; integration tests may hit host Ollama optionally.
- Embedding-based retrieval can be added without rewriting fast/detailed flows.
- Scoring container keeps **host network** to reach `127.0.0.1:11434`.
