"""Deterministic tests for host loopback HTTP proxy → Compose socket bridge."""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import host_http_proxy_socket as bridge


class HostHttpProxySocketTests(unittest.TestCase):
    def test_classify_loopback_http_proxy(self) -> None:
        self.assertEqual(bridge.classify_proxy("http://127.0.0.1:2080"), "loopback")
        self.assertEqual(bridge.classify_proxy("http://localhost:3128"), "loopback")

    def test_classify_remote_and_none(self) -> None:
        self.assertEqual(bridge.classify_proxy("http://proxy.example.test:8080"), "remote")
        self.assertEqual(bridge.classify_proxy(None), "none")
        self.assertEqual(bridge.classify_proxy("socks5://127.0.0.1:1080"), "none")

    def test_resolve_prefers_explicit_host_proxy_env(self) -> None:
        with patch.dict(
            "os.environ",
            {"JOB_SEARCH_HOST_HTTP_PROXY": "http://127.0.0.1:9999", "HTTP_PROXY": "http://127.0.0.1:1"},
            clear=False,
        ):
            self.assertEqual(bridge.resolve_host_proxy_url(), "http://127.0.0.1:9999")

    def test_override_template_uses_compose_service_not_loopback(self) -> None:
        self.assertIn("http://hh-egress:3128", bridge.OVERRIDE_TEMPLATE)
        self.assertNotIn("127.0.0.1:2080", bridge.OVERRIDE_TEMPLATE)
        self.assertIn("./.local/hh-host-http-proxy.sock", bridge.OVERRIDE_TEMPLATE)

    def test_makefile_wires_ensure_into_dev_up(self) -> None:
        makefile = (Path(__file__).resolve().parents[1] / "Makefile").read_text(encoding="utf-8")
        self.assertIn("host_http_proxy_socket.py ensure", makefile)
        self.assertIn("host_http_proxy_socket.py compose-files", makefile)
