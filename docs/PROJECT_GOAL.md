# Job Search — Project Goal

Canonical long-term product direction and permanent development guardrails.
This is **not** an implementation plan and **not** permission to start future
slices.

## Status

**PROJECT_GOAL → COMPLETE** (OWNER ACCEPTED Final Project Gate, 2026-09-09).

The product goal below is preserved as the accepted v1 definition and permanent
guardrails. Operational snapshot: [`PROJECT_STATUS.md`](../PROJECT_STATUS.md).
Remaining Roadmap items (including PB-11) are **POST-v1 / BACKLOG / OPTIONAL**
and must not be treated as blockers for this completed goal unless the owner
explicitly opens a new goal or slice.

Product ordering lives in the Google Drive document **Job Search**
(`Product Backlog`, `Roadmap`, current `R<N>` tab). Local docs such as
[`ARCHITECTURE_PLAN.md`](../ARCHITECTURE_PLAN.md) and
[`DEVELOPMENT_PROCESS.md`](../DEVELOPMENT_PROCESS.md) are implementation /
process projections — if they conflict with the Google Doc on product scope,
stop and report the conflict.

## Product goal

Довести Job Search до реально используемого локального продукта для
ежедневного поиска работы.

Главный критерий прогресса:

полезный end-to-end пользовательский flow,
а не архитектурная идеальность.

Target journey:

find
→ score
→ decide
→ act
→ response
→ hiring pipeline
→ offer
→ close search cycle

Follow canonical Product Backlog / Roadmap for product ordering.

## Development principles

- Делать небольшие работающие vertical slices.
- Сначала рабочий пользовательский сценарий, затем полировка.
- Не оптимизировать и не усложнять без наблюдаемой продуктовой причины.
- Не превращать единичные edge cases в длинную цепочку RCA, если основной
  продукт работает.
- Переиспользовать существующие сервисы и доменные сущности, а не создавать
  параллельные реализации.
- Предпочитать минимальное решение, достаточное для текущего product gate.
- Реальное E2E evidence важнее архитектурной красоты.

## Scope discipline

The current explicit user/Cursor task defines the ACTIVE SLICE.

PROJECT_GOAL describes direction, NOT permission to implement future work.

When a slice is complete:

- stop
- report
- wait for the next explicit task

Do NOT independently start the next Roadmap stage.

Do NOT expand scope merely because PROJECT_GOAL mentions a future capability.

## Architecture boundaries

Preserve accepted service responsibilities:

- Core = canonical product/domain state
- Web = user interface
- HH = HeadHunter integration/acquisition
- Scoring = semantic scoring service
- RabbitMQ = execution transport, not business source of truth
- OSINT = research capability

Reuse existing boundaries unless a concrete product requirement proves that
a change is necessary.

## Scoring policy

Current semantic scorer is considered GOOD ENOUGH for product development.

Do not tune:

- prompts
- schemas
- anchors
- repair behavior
- calibration
- semantic identity

unless:

- scoring blocks the product flow,
- errors become materially frequent,
- or the owner explicitly requests scorer work.

Rare terminal semantic errors are acceptable if they fail safely.

## Automation boundary

Background automation may:

fetch
→ ingest/dedupe
→ score

It must NOT automatically:

- apply to vacancies
- send recruiter/employer messages
- perform outreach
- change owner decisions

External actions require explicit owner intent unless a future accepted
product slice changes this rule.

## Human vs AI state

Keep separate:

- AI verdict
- owner decision
- action plan/channel
- actual application/outreach
- employer response
- hiring stage

Do not collapse these concepts into one status.

## Privacy

Owner-specific career/search preferences are private runtime data.

Never place real owner-specific criteria in:

- public Git
- public docs
- fixtures
- example configs
- logs
- telemetry

Public repository may contain only:

- schemas
- generic algorithms
- fake examples/templates

PersonalScoringProfile values remain private.

## Git / release discipline

- Do not push unless explicitly authorized by the owner.
- Commit completed accepted-slice work locally when the task requires it.
- Keep trees clean at slice completion.
- Do not silently rewrite historical evidence/data.
- Preserve provenance and migrations where required.

## Operational principle

Job Search should behave like a daily product, not a development demo.

Normal use should not require:

- Cursor
- ad-hoc terminal fixes
- manual container networking
- repeated setup after reboot

Operational complexity is justified only when required by product behavior.

## Definition of useful progress

Prefer work that makes the owner able to do the next real job-search action
inside Job Search.

When choosing between:

A. polishing an already-working internal subsystem

and

B. completing a missing user journey step

prefer B unless A is blocking reliability or correctness.

## Future R-slice prompts

Normal product-slice prompts should contain only:

- slice name
- accepted baseline / HEADs when necessary
- concrete goal
- slice-specific requirements
- acceptance
- tests / commit / report requirements

They should **not** repeatedly paste generic blocks already covered here
(no overengineering, privacy baseline, no push, scorer freeze, automation
safety) unless the slice specifically overrides or stresses that rule.
