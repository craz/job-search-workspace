"""Exercise the public PostgreSQL-Core-Web flow through Web HTTP.

The script sends a bounded create, status-update and list sequence to a
loopback-only Web endpoint selected by ``WEB_PORT``. Web is responsible for
forwarding those calls to Core; this script never receives database credentials
or addresses PostgreSQL. Every run generates a synthetic external identity and
prints exactly one JSON result. HTTP failures are decoded when possible and an
unsatisfied flow exits non-zero without modifying containers or volumes.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
import uuid


def request(method: str, path: str, payload: dict[str, str] | None = None) -> tuple[int, dict]:
    """Send one bounded JSON request to the loopback-only Web endpoint."""
    port = os.getenv("WEB_PORT", "8080")
    headers = {"Accept": "application/json"}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    if method == "POST":
        headers["Idempotency-Key"] = payload["external_id"] if payload else "smoke"
    call = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}", data=data, headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(call, timeout=10) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, json.load(error)


def main() -> int:
    """Create, update and re-read one synthetic vacancy through Web and Core."""
    identity = f"workspace-smoke-{uuid.uuid4()}"
    payload = {
        "company_name": "Workspace Smoke Labs",
        "company_external_id": "workspace-smoke-company",
        "source": "workspace-smoke",
        "external_id": identity,
        "title": "Synthetic Integration Engineer",
        "url": "https://example.com/workspace-smoke",
        "description": "Disposable synthetic compose smoke fixture.",
    }
    created_status, created = request("POST", "/api/v1/vacancies", payload)
    updated_status, updated = request(
        "PATCH", f"/api/v1/vacancies/{created.get('id', 'missing')}", {"status": "reviewing"}
    )
    listed_status, listed = request("GET", "/api/v1/vacancies")
    ok = (
        created_status == 201
        and updated_status == 200
        and updated.get("status") == "reviewing"
        and listed_status == 200
        and any(item.get("id") == created.get("id") for item in listed.get("items", []))
    )
    print(
        json.dumps(
            {
                "ok": ok,
                "created_status": created_status,
                "updated_status": updated_status,
                "listed_status": listed_status,
                "vacancy_id": created.get("id"),
            },
            sort_keys=True,
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
