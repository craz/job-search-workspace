# ADR-003: HTTP and JSON CLI service contracts

- Status: accepted
- Date: 2026-08-15

## Context

The services run locally in containers, while existing Hermes remains a local
host process. A single transport does not fit browser UI, service integration and
safe host automation equally well.

## Decision

- Core exposes versioned HTTP endpoints under `/api/v1`; OpenAPI is authoritative.
- Machine-facing commands expose versioned JSON CLI envelopes; JSON Schema is
  authoritative.
- Web uses Core HTTP only.
- Host Hermes uses public JSON CLI only.
- Provider changes remain backward compatible until consumers migrate.

## Consequences

- No cross-repository Python imports or shared application database.
- Contract tests are mandatory for providers and consumers.
- Requests require bounded timeouts and stable machine-readable errors.
- Breaking changes require a new major contract version and migration plan.
