# R2.2.2 — Official HH vacancy API capability probe

**Date:** 2026-08-27  
**Environment:** Compose service `hh` (healthy), egress `hh-egress:3128`,
`JOB_SEARCH_HH_API_URL=https://api.hh.ru`,
`JOB_SEARCH_HH_USER_AGENT=job-search-hh/0.1 (cccrazzz@gmail.com)`.  
**Writes:** none (GET only). **Browser vacancy search:** not attempted.  
**Status:** **BLOCKED · OWNER DECISION REQUIRED**

## Verdict

Official vacancy list and detail endpoints return **HTTP 403**
`{"errors":[{"type":"forbidden"}]}` in the normal Job Search application
path (container + proxy + configured User-Agent), including with a working
applicant Bearer token (`GET /me` = 200).

Non-vacancy public endpoints on the same egress succeed (`GET /dictionaries`
= 200). Therefore the failure is **vacancy-method policy / capability**, not
generic transport, missing User-Agent, or broken proxy.

Existing `vacancies sync` scaffold is **not** a capability proof.

## Exact probes

| Probe | Method | Auth | Status | Body / notes |
|---|---|---|---|---|
| `/vacancies?text=python&per_page=2&page=0` | GET | none | **403** | `errors:[{type:forbidden}]` |
| `/vacancies?text=python&per_page=1&page=0` | GET | Bearer (applicant) | **403** | same; `/me` with same token = **200** |
| `/vacancies` (no query) | GET | none | **403** | same |
| `/vacancies/123`, `/vacancies/1` | GET | none | **403** | same |
| `/employers/1455/vacancies/active?per_page=1` | GET | none | **403** | same |
| Alt UA / browserish UA on `/vacancies` | GET | none | **403** | same |
| `/dictionaries` | GET | none | **200** | OK on same proxy/UA |
| `/areas/1` | GET | none | **200** | OK |
| `/me` | GET | Bearer | **200** | token valid |

Sample request ids (403 list): `178785062090653f67e3fde3357ce004`,
`178785074020302c9cce64066e5d1007`.

Rate-limit headers (`Retry-After`, `X-RateLimit-*`) were **not** observed on
these 403 responses.

## Root cause (current evidence)

HH returns a bare API `forbidden` on vacancy search/detail for this applicant /
public client configuration. Same stack can call other `api.hh.ru` routes.
Public reporting (2026) documents that unauthenticated / non-approved
`GET /vacancies` access was closed; our live probe matches that class of
block. **Correct UA + applicant OAuth + Compose egress do not unlock vacancy
methods here.**

Not demonstrated as root cause: bad User-Agent format alone, missing proxy,
or empty token (token works for `/me`).

## Capability conclusions

| Capability | Result |
|---|---|
| Official list `GET /vacancies` | **Unavailable** (403) |
| Official detail `GET /vacancies/{id}` | **Unavailable** (403) |
| Live list field inventory | **Cannot establish** (no 200 body) |
| Live detail field inventory | **Cannot establish** |
| Live pagination metadata | **Cannot establish** |
| Acquisition DTO / multi-page transport implementation | **Not started** (gate) |
| Browser RO vacancy search | **Forbidden until OWNER ACCEPT** |

## Owner decision required

```text
Разрешать ли browser read-only vacancy search?
```

Existing browser RO approval for **own resumes** does **not** extend to
vacancy search.

Until explicit OWNER ACCEPT: do **not** implement browser vacancy transport;
do **not** start R2.2.3.
