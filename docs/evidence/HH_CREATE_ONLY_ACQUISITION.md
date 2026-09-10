# HH CREATE-ONLY ACQUISITION — live evidence

**When (UTC):** 2026-09-10T19:36–19:41Z  
**When (MSK):** 2026-09-10 22:36–22:41 MSK  
**push=0**

## Suitable create-only (max_pages=1)

- HTTP 200, top status=`partial`, code=`vacancy_detail_failed`
- SearchRun `69e6003a-3f91-445c-a62b-aee99a6de965` status=`partial`
- SERP checked: **50**
- already_in_db: **1**
- new_ids: **49**
- HH cards fetched: **49** (== new_ids)
- created: 0, updated: 0, detail_errors: 49
- SearchRun counters: found=50 created=0 updated=0 unchanged=1 errors=49
- Detail fetch failures: network_failure on NEW cards (Playwright); create-only gate still held (no detail for the 1 existing id).

## Manual refresh

- Web `POST /api/v1/vacancies/{id}/refresh-content` returns Russian UX envelope.
- Live attempt on existing `137206183`: ux_status=error / «Не удалось проверить» / code=browser_vacancy_read_failed (same Playwright network class as batch details). Curl via hh-egress to vacancy URL returns 302.

## Commits

See completion report.
