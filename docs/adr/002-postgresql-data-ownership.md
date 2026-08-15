# ADR-002: PostgreSQL owned exclusively by Core

- Status: accepted
- Date: 2026-08-15

## Context

Vacancies, companies, applications, metrics and contacts form a relational model
with integrity constraints and concurrent consumers. Sharing database access
between repositories would couple their release cycles and bypass public contracts.

## Decision

Use PostgreSQL 17 with SQLAlchemy 2.x and Alembic. Only Core receives application
database credentials and owns schema migrations. Other services communicate with
Core through versioned public interfaces.

## Consequences

- Relational constraints and transactions remain centralized.
- Integrations cannot read or mutate tables directly.
- Core availability becomes a dependency and requires health/readiness checks.
- PostgreSQL backup/restore enters workspace 0B with the first Core persistence slice.
