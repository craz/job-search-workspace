# PLAYWRIGHT HH DETAIL NETWORK RCA

**When (UTC):** 2026-09-10T20:30–20:48Z  
**When (MSK):** 2026-09-10 23:30–23:48 MSK  
**push=0**  
**Ports:** Web 18080 / Core 18000 / HH 8092

## Verdict

**Not a transport/proxy failure.** Chromium `page.goto` to vacancy URLs succeeded
(HTTP 302→200 via `hh-egress`). Detail path failed in `page.evaluate(DETAIL_EXTRACT_JS)`
with `SyntaxError: Identifier 'href' has already been declared`, caught as
`vacancy_detail_failed` and mapped by recovery to `network_failure`.

Root introduced in HH `f703531` (CAPTCHA fail-fast): added top-level
`const href = String(location.href || '')` in `DETAIL_EXTRACT_JS` without removing
the later `const href = location.href || ''`. SERP extract stayed valid (second
`href` is loop-scoped).

## Failed runs (before fix)

| Run | Result |
|---|---|
| `69e6003a-3f91-445c-a62b-aee99a6de965` | serp 50 / new 49 / detail_errors 49 / created 0 / `vacancy_detail_failed`+`network_failure` |
| `b34d507d-3214-414e-bb72-de95fb0778e1` | same class after CAPTCHA FP fix |

Picked vacancy id from `69e6003a`: **134000626**.

## Trace (after instrumentation / live reproduce)

- Exact URL: `https://hh.ru/vacancy/134000626`
- `page.goto`: status **200** (after 302 to `https://samara.hh.ru/vacancy/134000626`)
- final `page.url`: regional vacancy URL; title: vacancy title (not CAPTCHA)
- `requestfailed`: none on document navigation
- Exception on product path: `playwright._impl._errors.Error` /
  `Page.evaluate: SyntaxError: Identifier 'href' has already been declared`
- Chromium `net::ERR_*`: **none** (goto succeeded)
- Browser stderr: N/A (headless persistent context; failure is evaluate SyntaxError)

## curl vs Playwright (same HH egress)

| Probe | Result |
|---|---|
| Proxy | `http://hh-egress:3128` (env `HH_PROXY`/`HTTP(S)_PROXY`) |
| DNS | `hh-egress` → `172.20.0.2` |
| CONNECT `hh.ru:443` | `HTTP/1.1 200 Connection established` |
| curl `-x hh-egress` vacancy | **302** → `samara.hh.ru` |
| Playwright goto | **200** after redirect |
| Playwright `extract_detail_page` (before fix) | SyntaxError on `DETAIL_EXTRACT_JS` |

**WHY CURL WORKED BUT PRODUCT “NETWORK” FAILED:** curl only proves TLS/HTTP through
egress. Product detail ingest requires `DETAIL_EXTRACT_JS`; the duplicate `const href`
made every detail extract throw. Recovery taxonomy mapped `vacancy_detail_failed` →
`network_failure`, so operators saw a false transport RCA.

## Playwright proxy config (runtime proof)

- Explicit `proxy=` on `launch_persistent_context`: **no**
- Env-based: `HTTP_PROXY`/`HTTPS_PROXY`/`HH_PROXY=http://hh-egress:3128` passed
  (DISPLAY set → `env={**os.environ}`)
- `NO_PROXY` includes compose services + `hh-egress` (destination bypass list; proxy
  endpoint itself still used for hh.ru)
- Chromium argv: `--no-sandbox --disable-dev-shm-usage`; headless=True
- Loopback rewriting: compose/hh-egress bridge (not 127.0.0.1 inside container);
  `egress_diagnostic`: reachable + CONNECT ok; `misconfigured_loopback=false`

## Browser process / profile

- Persistent profile: `/var/lib/job-search-hh/profile`
- Headless product context; headed challenge/login uses same profile + ProfileLock
- During acceptance: no Singleton lock; no competing HH Chromium after restart
- CAPTCHA policy unchanged (no bypass)

## Classification

| Kind | Detector | This incident |
|---|---|---|
| Vacancy page | `/vacancy/<id>` + title/content | YES (goto ok) |
| Login | login selectors / path | no |
| CAPTCHA | URL/title/DOM phrase detectors | no (false Robotics FP was separate prior fix) |
| Transport | `ERR_PROXY_*` / CONNECT aborted / egress preflight | no |
| Extract runtime | `Page.evaluate` SyntaxError → `page_extract_failed` | YES (root) |

## Fix

1. Remove second `const href` in `DETAIL_EXTRACT_JS`; bump extractor to
   `hh-browser-vacancy-ro-v3`.
2. `_detail_failure_code`: evaluate/SyntaxError → `page_extract_failed` (not in
   recovery `_CODE_NETWORK`).
3. Regression tests: `tests/unit/test_vacancy_extract_js.py` + existing HTML fixture
   Playwright test green.

## Acceptance

| Gate | Result |
|---|---|
| A NEW detail+ingest `134000626` | `outcome=created`, ok |
| B EXISTING refresh `137206183` via Web | `ux_status=unchanged`, «Изменений нет» |
| E SMALL batch max_pages=1 run `a9cc7717…` | success; serp 50; already_in_db 2; new_ids 48; hh_cards_fetched 48; created 48; detail_errors 0; recovery none |

## Fixture href redeclare gate

Was red (`Identifier 'href' has already been declared` on detail fixture evaluate).
Now **green** via fix + `test_detail_extract_js_*` / `test_html_fixtures_extract_with_playwright`.
