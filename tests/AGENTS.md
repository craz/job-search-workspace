# Instructions for tests and BDD

1. Test observable contracts, negative paths and safety invariants with synthetic
   data; never use real tokens, profiles, volumes or external writes.
2. User-facing behavior starts with `Как [роль], Я хочу [действие], Чтобы
   [ценность]` and an executable Gherkin scenario under `tests/features/`.
3. Bind Python feature files through `pytest-bdd` when product dependencies are
   available; workspace bootstrap scenarios may use the documented stdlib runner.
4. Keep unit, integration, contract, BDD and smoke responsibilities distinct.
5. Warnings fail CI; every skip needs a concrete environmental reason.

