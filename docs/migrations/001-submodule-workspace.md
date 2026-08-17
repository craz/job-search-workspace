# Migration: sibling repositories to Git submodules

## Scope

Move workspace composition from sibling checkouts plus manifest/lock files to
six independently versioned submodules below `services/`. Product repository
history and existing sibling checkouts are preserved.

## Preconditions

- Every gitlink target commit is pushed to its canonical service remote.
- Service worktrees are clean and their `origin` URLs are verified.
- The workspace worktree is inspected; unrelated files are not staged.

## Forward migration

1. Publish the four existing green scaffold commits that were local-only.
2. Add Core, HH, Scoring, OSINT, Content, and Web under `services/`.
3. Set canonical GitHub URLs and `main` tracking branches in `.gitmodules`.
4. Remove `repos.yaml` and `repos.lock.json`; gitlinks replace both.
5. Change bootstrap and doctor to validate submodule state without mutating an
   initialized checkout.
6. Update architecture, process, feature specification, BDD, and unit gates.
7. Prove a recursive clone can resolve every recorded gitlink before publishing
   the workspace change.

## Compatibility and rollout

The migration changes only workspace composition. Service APIs, data formats,
runtime volumes, and release histories do not change. Existing sibling
checkouts remain valid but are no longer discovered by workspace commands.

Future service rollouts publish provider commits before consumer commits and
update the workspace gitlink only after compatibility gates pass.

## Rollback

Before the workspace migration commit is shared, rollback is a normal revert of
the staged workspace changes; sibling checkouts remain untouched. After sharing,
revert the workspace migration commit to restore ADR-001 tooling. Never delete
service remotes or rewrite service history as part of rollback.

## Verification

- `make bootstrap`
- `make doctor-offline`
- `make test`
- `git submodule status --recursive`
- clean recursive clone followed by `git submodule status --recursive`
