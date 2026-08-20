# ADR 004: Read-only OSINT research view in Web

- Status: Accepted
- Date: 2026-08-20

## Context

Core accepts confirmed normalized people only. OSINT owns unconfirmed evidence,
provider provenance and research reports. Showing proposals in the vacancy board
cannot be implemented through Core persistence without weakening both ownership
and confirmation rules.

## Decision

OSINT exposes a versioned HTTP API containing only normalized proposals: person
name, proposed title, confidence, source URL, bounded evidence excerpt,
observation time and confirmation state. Raw provider payloads remain private.

Web may read and trigger this bounded research API through its server-side
adapter. Core remains the only Web dependency for domain reads and writes. Web
does not access OSINT storage, provider APIs or another service's volume.

## Consequences

- The dashboard can display unverified research without treating it as a Person.
- OSINT availability has an independent loading/error state and cannot make the
  vacancy board unavailable.
- A future promotion to Core remains a separate explicit workflow.
