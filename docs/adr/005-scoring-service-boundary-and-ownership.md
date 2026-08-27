# ADR-005: Scoring service boundary and ownership

- Status: accepted (R2.3 architecture)
- Date: 2026-08-28

## Context

R2.2 delivers canonical Vacancies with `content_hash`, SearchRun provenance, and
scoring-ready `ResumeVersion` content in Core. PB-03 / Roadmap R2.3 require a
**Scoring service foundation** before mass list integration (R2.4) and detailed
scoring UX (R2.5).

A bootstrap worker already exists: JSON file queue, host Ollama, `POST
/api/v1/assessments` writeback. It embeds resume text in Ollama Modelfiles,
fetches vacancies via list-all, and has no policy versioning or HTTP product
surface.

## Decision

1. **Scoring remains a standalone service** — not part of Core or Web.
2. **Core owns canonical domain persistence:**
   - `Vacancy`, `CandidateProfile`, `ProfileVersion`, `ResumeVersion`
   - normalized **`Assessment`** as the durable ScoringResult store (extended in
     R2.3.1 for provenance/current-result metadata as needed)
3. **Scoring owns orchestration and private artifacts:**
   - signal calculation (future), context assembly, prompt construction
   - LLM calls via provider abstraction
   - job/queue lifecycle, raw LLM envelopes, lease/retry state in `scoring-state`
4. **Integration is HTTP/JSON only** — no cross-repo Python imports, no shared
   PostgreSQL access (ADR-002, ADR-003).
5. **Web consumes scores via Core API** in R2.4+; Scoring HTTP is the operator /
   future Web-proxy integration surface, not a second domain store.

## Consequences

- Scoring must assemble **scoring-ready context** from Core public contracts
  (`/api/v1/candidate-context`, vacancy read, resume version content) — not from
  private `data/resume.txt` alone.
- Assessment rows remain the audit/history anchor; **current result** selection
  is explicit (see ADR-006), not “latest row wins” implicitly.
- Queue/worker model is retained for local single-user batch evolution (R2.4);
  no Kafka/Celery/RabbitMQ.
- Detailed design: [`docs/SCORING_SERVICE.md`](../SCORING_SERVICE.md).
