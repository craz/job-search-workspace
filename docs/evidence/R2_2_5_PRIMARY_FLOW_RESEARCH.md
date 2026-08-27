# R2.2.5 — PRIMARY FLOW RESEARCH (ACCEPTED)

**Date:** 2026-08-27  
**Status:** PRIMARY FLOW RESEARCH = **OWNER ACCEPTED**  
**Correction implementation:** see `R2_2_5_WEB_VACANCY_SEARCH.md`

## Live probe (browser RO)

- Active resume (not hardcoded in product): title  
  `Project Manager / Руководитель IT-проектов`
- URL shape:
  `https://hh.ru/search/vacancy?resume={active_external_id}&from=resumelist&hhtmFromLabel=vacancies_for_resume_button&hhtmFrom=resume_list`
- Redirect: `*.hh.ru` (resume query preserved)
- found_text: **«Найдено … подходящих вакансии для резюме»** (order-of-magnitude ~2k)
- page 0 / page 1: **~50 cards each**, distinct external ids
- detail `/vacancy/{id}`: description present
- login_ready required; no CAPTCHA on probe

## Freshness / order (verified — proceed; reconfirmed 2026-08-27)

| UI / behaviour | Observed |
|---|---|
| Default / «По соответствию» | `order_by=relevance` |
| «По дате» / publication time | `order_by=publication_time` (normal HH Web URL) |
| Top-8 comparison | relevance vs publication_time: **0 overlap** |
| Total heading | «Найдено 2 272 подходящих вакансии для резюме» |

**Product default for `resume_suitable`:** `order_by=publication_time`.

## Legacy

Browser SERP with same `resume=` + `vacancies_for_resume_button` pattern  
(`/data/Projects/job_search` `hh_apply.primary_resume_search_url`).

No HH official suitable-vacancies API in legacy or current ref.
