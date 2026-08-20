"""Exercise the public PostgreSQL-Core-Web flow through loopback HTTP.

The script sends bounded Vacancy, Application, Daily Metric and Person
sequences to the Web endpoint selected by ``WEB_PORT``. Web forwards all
operations to Core; the script never receives
database credentials or addresses PostgreSQL. Every run generates synthetic
external identities and prints exactly one JSON result. HTTP failures are
decoded when possible and an unsatisfied flow exits non-zero without modifying
containers or volumes.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
import uuid


def request(
    method: str,
    path: str,
    payload: dict[str, object] | None = None,
    *,
    idempotency_key: str | None = None,
) -> tuple[int, dict]:
    """Send one bounded JSON request to the loopback-only Web endpoint."""
    port = os.getenv("WEB_PORT", "8080")
    headers = {"Accept": "application/json"}
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    if idempotency_key is not None:
        headers["Idempotency-Key"] = idempotency_key
    call = urllib.request.Request(
        f"http://127.0.0.1:{port}{path}", data=data, headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(call, timeout=10) as response:
            return response.status, json.load(response)
    except urllib.error.HTTPError as error:
        return error.code, json.load(error)


def main() -> int:
    """Persist one synthetic, linked workflow through Web and Core."""
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
    created_status, created = request(
        "POST", "/api/v1/vacancies", payload, idempotency_key=identity
    )
    updated_status, updated = request(
        "PATCH", f"/api/v1/vacancies/{created.get('id', 'missing')}", {"status": "reviewing"}
    )
    listed_status, listed = request("GET", "/api/v1/vacancies")
    application_payload = {
        "vacancy_id": created.get("id", "missing"),
        "source": "workspace-smoke",
        "external_id": f"workspace-application-{uuid.uuid4()}",
        "resume_version": "synthetic-v1",
        "next_action": "Verify the local Application journal",
    }
    application_status, application = request(
        "POST",
        "/api/v1/applications",
        application_payload,
        idempotency_key=str(application_payload["external_id"]),
    )
    applications_status, applications = request("GET", "/api/v1/applications")
    metric_date = "2026-08-20"
    metric_key = f"workspace-metric-{uuid.uuid4()}"
    metric_status, metric = request(
        "PUT",
        f"/api/v1/metrics/{metric_date}",
        {
            "metric_date": metric_date,
            "applications": 1,
            "views_new": 2,
            "notes": "Synthetic Compose smoke",
        },
        idempotency_key=metric_key,
    )
    metrics_status, metrics = request("GET", "/api/v1/metrics")
    person_payload = {
        "company_id": created.get("company", {}).get("id", "missing"),
        "vacancy_id": created.get("id", "missing"),
        "source": "workspace-smoke",
        "external_id": f"workspace-person-{uuid.uuid4()}",
        "full_name": "Alex Smoke",
        "role": "referral",
        "title": "Synthetic Integration Contact",
        "notes": "Disposable confirmed Compose smoke fixture.",
    }
    person_status, person = request(
        "POST", "/api/v1/people", person_payload,
        idempotency_key=str(person_payload["external_id"]),
    )
    person_updated_status, person_updated = request(
        "PATCH", f"/api/v1/people/{person.get('id', 'missing')}",
        {"status": "researching"},
    )
    people_status, people = request("GET", "/api/v1/people")
    ok = (
        created_status == 201
        and updated_status == 200
        and updated.get("status") == "reviewing"
        and listed_status == 200
        and any(item.get("id") == created.get("id") for item in listed.get("items", []))
        and application_status == 201
        and application.get("vacancy", {}).get("id") == created.get("id")
        and applications_status == 200
        and any(
            item.get("id") == application.get("id") for item in applications.get("items", [])
        )
        and metric_status in {200, 201}
        and metric.get("metric_date") == metric_date
        and metric.get("applications") == 1
        and metrics_status == 200
        and any(item.get("metric_date") == metric_date for item in metrics.get("items", []))
        and person_status == 201
        and person.get("vacancy", {}).get("id") == created.get("id")
        and person_updated_status == 200
        and person_updated.get("status") == "researching"
        and people_status == 200
        and any(item.get("id") == person.get("id") for item in people.get("items", []))
    )
    print(
        json.dumps(
            {
                "ok": ok,
                "created_status": created_status,
                "updated_status": updated_status,
                "listed_status": listed_status,
                "application_status": application_status,
                "applications_status": applications_status,
                "metric_status": metric_status,
                "metrics_status": metrics_status,
                "person_status": person_status,
                "person_updated_status": person_updated_status,
                "people_status": people_status,
                "vacancy_id": created.get("id"),
                "application_id": application.get("id"),
                "person_id": person.get("id"),
            },
            sort_keys=True,
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
