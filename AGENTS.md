# Global instructions for development agents

Long-term product direction: [`docs/PROJECT_GOAL.md`](docs/PROJECT_GOAL.md).
Always-on guardrails live in `.cursor/rules/project-goal.mdc` and
`.cursor/rules/00-project-context.mdc` (scope, STOP, ACCEPT≠COMPLETE, privacy,
no-push, external writes, service boundaries). This file describes **how** to
work in the repository; it does not replace those rules or the goal.

1. Read `ARCHITECTURE_PLAN.md` and the nearest nested `AGENTS.md` / service
   `.cursor/rules` before a non-trivial change; never commit or quote private
   `.local/` content.
2. Inspect current code, tests and Git state before editing; keep scope coherent
   and preserve unrelated user changes.
3. Use versioned HTTP/JSON CLI contracts; significant architectural choices need
   an ADR and incompatible changes need a migration plan.
4. Run applicable quality gates and report exact pass/fail/skip results. Warnings
   are defects unless their external cause is explicitly demonstrated.
5. Keep implementation and documentation truthful, reproducible and understandable
   without chat context; never present planned behavior as implemented.
6. Detailed development cycle and acceptance checklist:
   `DEVELOPMENT_PROCESS.md` / `.cursor/rules/10-development-workflow.mdc`.
7. Before naming a long-lived service instance or infrastructure entity, read
   `NAMING_CONVENTION.md`, check `USED`, use the class-appropriate canonical
   slug, and register only after assignment. Ordinary Compose services and
   ephemeral containers stay functionally named.
8. Project hook synchronizes raw history after each turn; use
   `make ai-history-sync` as a fallback. After a completed engineering step,
   update `.local/AI_HISTORY.md` without quoting it.
