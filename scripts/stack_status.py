#!/usr/bin/env python3
"""Print a compact local stack readiness summary for operators (R2.5.2)."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _load_dotenv() -> None:
    env_path = ROOT / ".env"
    if not env_path.is_file():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip().strip('"').strip("'")


_load_dotenv()


def _port(name: str, default: str) -> str:
    value = (os.environ.get(name) or "").strip()
    return value or default


CORE = os.environ.get("CORE_BASE_URL") or f"http://127.0.0.1:{_port('CORE_PORT', '8000')}"
WEB = os.environ.get("WEB_BASE_URL") or f"http://127.0.0.1:{_port('WEB_PORT', '8080')}"
SCORING = os.environ.get("SCORING_BASE_URL") or f"http://127.0.0.1:{_port('SCORING_PORT', '8090')}"
HH = os.environ.get("HH_BASE_URL") or f"http://127.0.0.1:{_port('HH_API_PORT', '8092')}"
AUTOMATION = (
    os.environ.get("AUTOMATION_BASE_URL")
    or f"http://127.0.0.1:{_port('AUTOMATION_PORT', '8095')}"
)


def probe(name: str, url: str) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(url, timeout=3) as response:
            body = response.read().decode("utf-8", errors="replace")
            payload: Any
            try:
                payload = json.loads(body)
            except json.JSONDecodeError:
                payload = body[:120]
            return {"service": name, "ok": 200 <= response.status < 300, "status": response.status, "body": payload}
    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            payload = body[:120]
        return {"service": name, "ok": False, "status": error.code, "body": payload}
    except Exception as error:  # noqa: BLE001 - operator summary must never crash
        return {"service": name, "ok": False, "status": None, "error": str(error)}


def main() -> int:
    rows = [
        probe("core", f"{CORE.rstrip('/')}/health/ready"),
        probe("web", f"{WEB.rstrip('/')}/"),
        probe("scoring", f"{SCORING.rstrip('/')}/health/ready"),
        probe("hh", f"{HH.rstrip('/')}/health/ready"),
        probe("automation", f"{AUTOMATION.rstrip('/')}/health/ready"),
    ]
    for row in rows:
        mark = "OK" if row.get("ok") else "DOWN"
        detail = row.get("status") or row.get("error") or ""
        print(f"{row['service']:11} {mark:4} {detail}")
        if row["service"] == "hh" and isinstance(row.get("body"), dict):
            egress = row["body"].get("egress") or {}
            if egress:
                print(
                    f"            egress proxy_reachable={egress.get('proxy_reachable')} "
                    f"url={egress.get('proxy_url')}"
                )
        if row["service"] == "automation" and row.get("ok"):
            auto = probe("automation-status", f"{AUTOMATION.rstrip('/')}/api/v1/automation/status")
            body = auto.get("body") if isinstance(auto.get("body"), dict) else {}
            print(
                f"            enabled={body.get('enabled')} "
                f"running={body.get('running')} "
                f"last={body.get('last_status')}"
            )
    return 0 if all(row.get("ok") for row in rows[:3]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
