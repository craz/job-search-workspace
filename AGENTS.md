# Instructions for development agents

1. Read `ARCHITECTURE_PLAN.md`, `DEVELOPMENT_PROCESS.md` and, when present,
   `.project-context.local.md` before planning or changing the system. The local
   context is private and must never be committed.
2. Preserve repository boundaries: no cross-repository Python imports, shared
   databases, or access to another service's Docker volume.
3. Explore the current implementation and tests before asking discoverable
   questions or editing files.
4. Define scope, non-scope and acceptance criteria before non-trivial work.
5. Express every user-facing feature as `Как [роль], Я хочу [действие], Чтобы
   [ценность]`, then define executable Gherkin scenarios before implementation.
6. Use contract-first design for HTTP, JSON CLI and database changes.
7. Make the smallest coherent change; do not refactor unrelated code.
8. Run relevant quality gates, including `make bdd` when applicable, and report
   exact commands and results.
9. Never expose secrets, cookies, tokens, browser profiles or personal data.
10. Do not send real HH applications or Telegram messages without explicit user
   authorization.
11. Automatically commit each completed, green logical step. Stage only files
    from the current task and preserve unrelated user changes. Never push, open
    or merge a PR unless the user requested that remote Git operation.
12. Use `direnv` for interactive host-shell activation and repository
    `ensure-venv`/Make commands as the non-interactive fallback. Never require
    manual virtualenv activation or modify global Python.
13. For UI work, use the live development stack, verify in a browser when
    available, and preserve Docker volumes across reload/restart.
14. Update README/spec/contracts/runbooks/CHANGELOG together with behavior.
15. Keep every public repository honest, reproducible, understandable without
    chat context, and free of secrets, personal data, private correspondence and
    raw AI prose.
16. Follow `docs/AI_HISTORY.md`: keep raw and summary AI histories under the
    ignored `.local/` directory, redact sensitive data, and never commit them.
