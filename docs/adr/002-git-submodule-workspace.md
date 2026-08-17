# ADR-002: Git-submodule service workspace

- Status: accepted
- Date: 2026-08-17
- Supersedes: ADR-001

## Context

The product needs independently versioned service repositories with separate
remotes, pull requests, CI, and releases. Developers also need one project tree
that exposes all service code to the IDE and one standard Git mechanism for
reproducing the compatible revision set.

ADR-001 placed service checkouts beside the workspace and duplicated Git's
revision model with `repos.yaml` plus `repos.lock.json`. That preserved service
independence but made navigation surprising and required custom clone/lock
semantics.

## Decision

Keep every service as an independent repository and mount it below
`services/<name>` using Git submodules. `.gitmodules` is the service manifest and
the superproject's mode-160000 gitlinks are the compatible commit lock.

`bootstrap` initializes only absent submodules. It never updates, resets, cleans,
or switches an existing checkout. `doctor` verifies declarations, canonical
origins, gitlink equality, cleanliness, tools, and optionally remote branches.

Service changes follow this order:

1. Commit and push a green change in the service repository.
2. Update that service's gitlink in the workspace.
3. Run workspace integration gates.
4. Commit and push the workspace revision update.

## Consequences

- One workspace checkout exposes all service code under `services/`.
- Services retain independent histories, remotes, CI, and releases.
- Git natively records the tested compatible revision set.
- Clones must use `--recurse-submodules` or run `make bootstrap` afterward.
- A service commit must be reachable from its remote before its gitlink is
  published by the workspace.
- Cross-repository atomic commits remain impossible; compatibility still uses
  provider-before-consumer rollout.
- Developers must deliberately create or switch a branch inside a submodule
  before editing when Git initialized it at a detached HEAD.

## Rejected alternatives

- A single-repository monorepo removes independent remotes and release cycles.
- Sibling manifest-managed checkouts do not provide the requested single IDE
  tree and duplicate native gitlink behavior.
- Git subtree copies history into the workspace and complicates bidirectional
  synchronization with service remotes.
