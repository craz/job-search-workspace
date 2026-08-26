# HH Docker egress via host HTTP proxy

## Problem

Some Linux Docker setups **block container → host gateway TCP**
(`host.docker.internal` / bridge IP). A host HTTP proxy bound only to
`127.0.0.1` is then unreachable from the HH container, while the same proxy
works for host processes. Direct TLS from the container to `api.hh.ru` may also
fail when the operator network requires that proxy.

## Supported path

Documented startup (`make up` / `make dev`) runs
[`scripts/host_http_proxy_socket.py`](../../scripts/host_http_proxy_socket.py):

1. Reads the operator HTTP proxy URL from `JOB_SEARCH_HOST_HTTP_PROXY` or
   `services/hh/.env` (`HTTP_PROXY` / `HTTPS_PROXY` / `HH_PROXY`).
2. If the proxy host is **loopback**, starts a local Unix-socket relay under
   `.local/hh-host-http-proxy.sock` (gitignored) and writes
   `.local/docker-compose.hh-egress.yml`.
3. Compose attaches functional service `hh-egress`, which listens on the Docker
   network and connects to that socket.
4. HH container `HTTP(S)_PROXY` is rewritten to `http://hh-egress:3128`.

No manual `socat` / acceptance-only sidecar is required.

## Configuration

| Variable | Meaning |
|---|---|
| `JOB_SEARCH_HOST_HTTP_PROXY` | Preferred explicit host HTTP proxy URL (`http://127.0.0.1:PORT`) |
| `HTTP_PROXY` / `HTTPS_PROXY` in `services/hh/.env` | Used when the explicit variable is unset |
| `JOB_SEARCH_HH_HOST_PROXY_MODE` | `auto` (default), `off`, `loopback`, `remote` |

Protocol must be an **HTTP proxy** URL (HTTP CONNECT). Do not put SOCKS URLs in
these variables for this bridge.

Never commit proxy credentials. Prefer a local-only proxy without basic-auth in
the URL when possible.

## Commands

```bash
make hh-host-proxy-ensure   # create socket + Compose override when needed
make up                     # ensure + docker compose up -d --build
make down                   # compose down + stop socket relay
```

## Failure behavior

If the host proxy or `hh-egress` path is down, HH `GET /api/v1/account` returns
normalized `status=unavailable` / upstream failure — not a fake empty account
and not `not_authorized` from a missing profile.
