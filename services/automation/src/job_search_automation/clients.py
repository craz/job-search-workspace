"""HTTP clients for Core, HH and Scoring used by the automation cycle."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


class HttpError(RuntimeError):
    def __init__(self, code: str, message: str, *, status: int | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


class JsonHttpClient:
    def __init__(self, base_url: str, *, timeout_seconds: float = 60.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def request(
        self,
        method: str,
        path: str,
        *,
        body: dict[str, Any] | None = None,
        timeout_seconds: float | None = None,
    ) -> tuple[int, Any]:
        url = f"{self.base_url}{path}"
        data = None
        headers = {"Accept": "application/json"}
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(
                request, timeout=timeout_seconds or self.timeout_seconds
            ) as response:
                raw = response.read().decode("utf-8", errors="replace")
                payload: Any
                if not raw.strip():
                    payload = None
                else:
                    try:
                        payload = json.loads(raw)
                    except json.JSONDecodeError:
                        payload = raw
                return int(response.status), payload
        except urllib.error.HTTPError as error:
            raw = error.read().decode("utf-8", errors="replace")
            try:
                payload = json.loads(raw) if raw.strip() else {}
            except json.JSONDecodeError:
                payload = {"message": raw[:300]}
            if isinstance(payload, dict):
                code = str(payload.get("code") or payload.get("detail") or f"http_{error.code}")
                message = str(
                    payload.get("message")
                    or (
                        payload.get("detail", {}).get("message")
                        if isinstance(payload.get("detail"), dict)
                        else payload.get("detail")
                    )
                    or code
                )
            else:
                code = f"http_{error.code}"
                message = str(payload)[:300]
            raise HttpError(code, message, status=int(error.code)) from error
        except urllib.error.URLError as error:
            raise HttpError("unreachable", str(error.reason or error), status=None) from error


class CoreClient:
    def __init__(self, base_url: str, *, timeout_seconds: float = 60.0) -> None:
        self._http = JsonHttpClient(base_url, timeout_seconds=timeout_seconds)

    def health_ready(self) -> None:
        status, _ = self._http.request("GET", "/health/ready", timeout_seconds=5)
        if status >= 400:
            raise HttpError("core_unhealthy", f"status={status}", status=status)

    def search_run_items(self, search_run_id: str) -> list[dict[str, Any]]:
        _, payload = self._http.request("GET", f"/api/v1/search-runs/{search_run_id}/items")
        if isinstance(payload, dict) and isinstance(payload.get("items"), list):
            return [item for item in payload["items"] if isinstance(item, dict)]
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        return []

    def vacancy(self, vacancy_id: str) -> dict[str, Any]:
        _, payload = self._http.request("GET", f"/api/v1/vacancies/{vacancy_id}")
        if not isinstance(payload, dict):
            raise HttpError("invalid_vacancy", "vacancy payload is not an object")
        return payload


class HhClient:
    def __init__(self, base_url: str, *, timeout_seconds: float = 600.0) -> None:
        self._http = JsonHttpClient(base_url, timeout_seconds=timeout_seconds)

    def health_ready(self) -> dict[str, Any]:
        status, payload = self._http.request("GET", "/health/ready", timeout_seconds=5)
        if not isinstance(payload, dict):
            raise HttpError("hh_unhealthy", f"status={status}", status=status)
        if status >= 400:
            raise HttpError(
                str(payload.get("code") or "hh_unhealthy"),
                str(payload.get("message") or "HH not ready"),
                status=status,
            )
        return payload

    def run_suitable(self, *, max_pages: int = 1) -> dict[str, Any]:
        _, payload = self._http.request(
            "POST",
            "/api/v1/vacancies/suitable",
            body={"execution": {"order": "publication_time", "max_pages": max_pages}},
        )
        if not isinstance(payload, dict):
            raise HttpError("hh_suitable_invalid", "suitable response is not an object")
        return payload


class ScoringClient:
    def __init__(self, base_url: str, *, timeout_seconds: float = 120.0) -> None:
        self._http = JsonHttpClient(base_url, timeout_seconds=timeout_seconds)

    def health_ready(self) -> None:
        status, _ = self._http.request("GET", "/health/ready", timeout_seconds=5)
        if status >= 400:
            raise HttpError("scoring_unhealthy", f"status={status}", status=status)

    def scoring_state(self, vacancy_id: str) -> dict[str, Any]:
        _, payload = self._http.request(
            "GET", f"/api/v1/vacancies/{vacancy_id}/scoring-state"
        )
        if not isinstance(payload, dict):
            raise HttpError("invalid_scoring_state", "scoring-state payload is not an object")
        return payload

    def enqueue_semantic_v1(self, vacancy_id: str) -> dict[str, Any]:
        status, payload = self._http.request(
            "POST",
            "/api/v1/score/semantic-v1",
            body={"vacancy_id": vacancy_id},
            timeout_seconds=120,
        )
        if not isinstance(payload, dict):
            raise HttpError("invalid_enqueue", "enqueue payload is not an object", status=status)
        return payload
