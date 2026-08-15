# Global instructions for development agents

1. Read `ARCHITECTURE_PLAN.md` and applicable local instructions before a
   non-trivial change; never commit or quote private `.local/` content.
2. Preserve repository boundaries: no cross-repository Python imports, shared
   application database or access to another service's volume.
3. Inspect current code, tests and Git state before editing; keep scope coherent
   and preserve unrelated user changes.
4. Never expose secrets, cookies, browser profiles, personal data or private AI
   history. Use synthetic public examples and fixtures.
5. Never send real HH applications, Telegram messages or other external writes
   without explicit authorization.
6. Use versioned HTTP/JSON CLI contracts; significant architectural choices need
   an ADR and incompatible changes need a migration plan.
7. Run applicable quality gates and report exact pass/fail/skip results. Warnings
   are defects unless their external cause is explicitly demonstrated.
8. Keep implementation and documentation truthful, reproducible and understandable
   without chat context; never present planned behavior as implemented.
9. Automatically commit only a completed green logical step, staging only task
   files. Never push, create/merge a PR, tag or release without explicit request.
10. Follow the nearest nested `AGENTS.md` for scripts, tests or documentation;
    narrower instructions extend and override this global minimum.
