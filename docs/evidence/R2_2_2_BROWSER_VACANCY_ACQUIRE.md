# R2.2.2 — Browser RO vacancy acquisition evidence

**Date:** 2026-08-27  
**Owner decision:** YES — browser read-only vacancy search/detail APPROVED.  
**Status:** READY FOR OWNER ACCEPTANCE (implementation local; not pushed)

## Transport

Explicit selection only (`--transport browser|official|fixture`).  
No silent official→browser fallback.

Live command (Compose `hh`, persistent profile, headless Chromium):

```bash
python -m job_search_hh.cli vacancies acquire \
  --transport browser --text python --area 1 --search-field name \
  --order publication_time --max-pages 2 --detail-limit 1 --fetch-details
```

## Live bounded result (harmless query `python`, area=1)

| Check | Result |
|---|---|
| Envelope ok / status | `ok=true`, `status=available`, `code=ready` |
| Transport | `browser_readonly` |
| Search URL strategy | `https://hh.ru/search/vacancy?text&area&search_field&order_by&page` |
| Page 0 | ok, **50** summaries |
| Page 1 | ok, **50** summaries |
| Pagination | `pages_fetched=2`, `observed_page_size=50`, `max_pages_reached=true`, `exhausted=false`, `found_text` present |
| Sample external_id | `136706048` |
| Sample title / url / employer / area | present (`Okkam`, `https://hh.ru/vacancy/136706048`, Москва) |
| Detail description length | **3416** chars |
| HH writes | `false` |
| Core ingestion | `false` |
| Recovery | `none` |

Official API remains 403 (prior probe); browser path is the supported R2.2.2 transport.

## Deterministic gates

HH `make test`: unit 111 passed + 1 skipped (host without Playwright browsers),
contract 13, bdd 13 — green.
