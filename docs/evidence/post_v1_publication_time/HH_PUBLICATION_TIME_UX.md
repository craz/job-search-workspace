# POST-v1 — HH publication time + truthful freshness UX

**Date:** 2026-09-11 (MSK)  
**push=0**

## Exact publication datetime source (no extra request)

On a successfully fetched HH vacancy detail HTML (`https://hh.ru/vacancy/134000626` via hh-egress):

| Source | Field | Example |
|---|---|---|
| **Primary** | JSON-LD `JobPosting.datePosted` | `2026-09-10T17:36:58.633+03:00` |
| Fallback | Page state `publicationTime.$` (HTML-escaped in scripts) | same ISO |
| Display-only | Visible «Вакансия опубликована …» / `published_text` | not a reliable ISO |
| SERP UI | `vacancy-serp-item-activity` («Сегодня») | relative, not ISO |

Create-only batch already detail-fetches NEW ids only; extractor reads JSON-LD from that same page.

## Live suitable evidence

- `POST /api/v1/hh/vacancies/suitable` `max_pages=1` `start_page=0`
- run_id `fc6da1fa-ec9f-48ab-9fa7-cdc18a7759c7`
- `hh_cards_fetched == new_ids == 3` (no batch detail backfill)
- pagination: `more_remaining=true`, `max_pages_reached=true`, `found/source_total=2831`

### Created vacancies

| external_id | source_published_at (UTC) | first_seen_at (UTC) | Δ (found − published) |
|---|---|---|---|
| 137224132 | 2026-09-10T20:57:10.242Z | 2026-09-10T21:19:31.060Z | ~22m |
| 137224131 | 2026-09-10T20:56:57.731Z | 2026-09-10T21:19:31.078Z | ~22m |
| 137224093 | 2026-09-10T20:46:18.119Z | 2026-09-10T21:19:31.096Z | ~33m |

## Browser smoke

Screenshot: `docs/evidence/post_v1_publication_time/vacancies_list.png`

- Rows with `source_published_at`: «Опубликована: …»
- Rows without: «Найдена: …» (`first_seen_at`)
- Progress: «Проверено 50 из 2 831 · страница HH 0 · можно загрузить ещё»
