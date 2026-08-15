# Instructions for development agents

1. Read `ARCHITECTURE_PLAN.md` and `DEVELOPMENT_PROCESS.md` before planning or
   changing the system.
2. Preserve repository boundaries: no cross-repository Python imports, shared
   databases, or access to another service's Docker volume.
3. Explore the current implementation and tests before asking discoverable
   questions or editing files.
4. Define scope, non-scope and acceptance criteria before non-trivial work.
5. Use contract-first design for HTTP, JSON CLI and database changes.
6. Make the smallest coherent change; do not refactor unrelated code.
7. Run relevant quality gates and report exact commands and results.
8. Never expose secrets, cookies, tokens, browser profiles or personal data.
9. Do not send real HH applications or Telegram messages without explicit user
   authorization.
10. Automatically commit each completed, green logical step. Stage only files
    from the current task and preserve unrelated user changes. Never push, open
    or merge a PR unless the user requested that remote Git operation.
11. Use `direnv` for interactive host-shell activation and repository
    `ensure-venv`/Make commands as the non-interactive fallback. Never require
    manual virtualenv activation or modify global Python.
12. For UI work, use the live development stack, verify in a browser when
    available, and preserve Docker volumes across reload/restart.
13. Update README/spec/contracts/runbooks/CHANGELOG together with behavior.
