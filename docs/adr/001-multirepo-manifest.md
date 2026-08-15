# ADR-001: Manifest-managed multirepo workspace

- Status: accepted
- Date: 2026-08-15

## Context

The system is split into independently versioned repositories but must remain
reproducible as one local development environment. Git submodules would expose
Git-specific checkout state inside the workspace and complicate independent
repository workflows.

## Decision

Use a manifest repository with `repos.yaml` for repository identity and
`repos.lock.json` for the tested commit set. Bootstrap clones missing repositories
as siblings and never resets or cleans an existing checkout.

`repos.yaml` uses JSON syntax, which is valid YAML, so stdlib Python can parse it
without adding a bootstrap dependency.

## Consequences

- Product repositories remain ordinary independent Git repositories.
- A lock update is explicit and reviewable.
- Workspace scripts must validate manifest/lock consistency.
- Cross-repository atomic commits are not supported; compatibility is achieved
  through versioned contracts and provider-before-consumer rollout.
