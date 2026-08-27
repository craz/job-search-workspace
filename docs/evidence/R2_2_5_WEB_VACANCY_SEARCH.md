# R2.2.5 — Web vacancy search evidence

**Date:** 2026-08-27  
**Status:** READY FOR OWNER ACCEPTANCE (local; **not** pushed)

## Live Web URL

http://127.0.0.1:18080/#vacancies

## Timeout / proxy verification

| Path | Result |
|---|---|
| Web `POST /api/v1/hh/vacancies/search` | success in **~144s** |
| HH proxy timeout | **180s** (measured R2.2.4 ~151s) |
| Failure mode | would surface as `hh_unavailable` / fetch error — not silent |

Repeat-run via Web proxy: found=50, created=0, updated=0, unchanged=50.

## Gates

Web: unit 5 · integration 34 · contract 6 · bdd 10  
Core/HH regressions unchanged from R2.2.4 push.

## Non-scope

R2.2.A / R2.3 **NOT STARTED**. R2.2.5 **not pushed**.
