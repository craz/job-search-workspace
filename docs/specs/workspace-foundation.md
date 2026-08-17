# Feature: Reproducible multirepo workspace

## User Story

```text
Как разработчик системы,
Я хочу получить и проверить совместимые репозитории из одного workspace,
Чтобы начинать работу с известного воспроизводимого состояния.
```

## Scope

**In scope:** submodule manifest, gitlink lock, safe bootstrap, local/network
doctor, ADR.

**Non-scope:** Compose services, application tests, PostgreSQL backup/restore and
deployment. These capabilities enter workspace 0B with their owning components.

## Acceptance criteria

Executable scenarios are stored in
`tests/features/workspace_foundation.feature` and bound by
`tests/test_workspace_bdd.py`.

## Contracts

- `.gitmodules` declares six canonical service remotes below `services/`.
- Workspace gitlinks are the machine-readable compatible commit set.
- `scripts/workspace.py bootstrap` initializes only missing submodules and never
  resets an existing checkout.
- `scripts/workspace.py doctor` validates tools, origins, gitlink HEADs,
  worktree state and remote branches.
- `doctor --offline` skips remote access but still validates local state.

## Failure behavior

- Uninitialized submodule: error in doctor, initialized by bootstrap.
- Existing non-Git path: error, never overwrite.
- Origin mismatch: error, never rewrite automatically.
- Gitlink mismatch: warning in bootstrap, error in doctor.
- Dirty worktree: warning, never clean automatically.
- Missing tool or unreachable required remote: error.
