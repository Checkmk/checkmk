#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import asyncio
import functools
import json
import os
import socket
import ssl
import threading
from collections.abc import Iterator
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import override
from unittest.mock import Mock

import httpx2
import pytest

from cmk.crypto.certificate import CertificateWithPrivateKey
from cmk.livestatus_client import SingleSiteConnection
from cmk.maps.backend.connections.livestatus import LivestatusConnection
from cmk.maps.backend.core.config import settings


@functools.cache
def _ca_pem(common_name: str) -> bytes:
    ca = CertificateWithPrivateKey.generate_self_signed(
        common_name=common_name, organization="test", key_size=1024, is_ca=True
    )
    return ca.certificate.dump_pem().bytes


def _write_ca(path: Path, common_name: str) -> None:
    path.write_bytes(_ca_pem(common_name))


def _trusts(context: ssl.SSLContext | bool, common_name: str) -> bool:
    assert isinstance(context, ssl.SSLContext)
    der = ssl.PEM_cert_to_DER_cert(_ca_pem(common_name).decode())
    return der in context.get_ca_certs(binary_form=True)


@pytest.fixture(name="ca_file")
def fixture_ca_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    monkeypatch.setattr(settings, "checkmk_omd_root", str(tmp_path))
    ca_dir = tmp_path / "var" / "ssl"
    ca_dir.mkdir(parents=True)
    return ca_dir / "ca-certificates.crt"


def test_rest_calls_skip_verification_when_it_is_off(ca_file: Path) -> None:
    _write_ca(ca_file, "site-ca")
    assert LivestatusConnection(tls_verify=False)._rest_tls is False  # noqa: SLF001


@pytest.mark.usefixtures("ca_file")
def test_rest_calls_trust_the_system_without_site_cas() -> None:
    assert LivestatusConnection()._rest_tls is True  # noqa: SLF001


def test_rest_calls_trust_the_site_cas(ca_file: Path) -> None:
    _write_ca(ca_file, "site-ca")
    assert _trusts(LivestatusConnection()._rest_tls, "site-ca")  # noqa: SLF001


def test_rest_calls_trust_site_cas_written_anew(ca_file: Path) -> None:
    connection = LivestatusConnection()
    _write_ca(ca_file, "old-ca")
    assert _trusts(connection._rest_tls, "old-ca")  # noqa: SLF001
    _write_ca(ca_file, "new-ca")
    mtime = ca_file.stat().st_mtime_ns + 1_000_000_000
    os.utime(ca_file, ns=(mtime, mtime))
    context = connection._rest_tls  # noqa: SLF001
    assert _trusts(context, "new-ca")
    assert not _trusts(context, "old-ca")


_METRIC_ANSWER = {
    "step": 60,
    "time_range": {"start": "2026-01-01T00:00:00+00:00"},
    "metrics": [{"data_points": [1.0], "unit": {"symbol": ""}, "title": "Load"}],
}


def _metric_answer(_request: httpx2.Request) -> httpx2.Response:
    return httpx2.Response(HTTPStatus.OK, json=_METRIC_ANSWER)


class _MetricHandler(BaseHTTPRequestHandler):
    """Answers every POST with a metric, as a site or a proxy in front of one would."""

    def do_POST(self) -> None:
        self.rfile.read(int(self.headers.get("Content-Length", "0")))
        body = json.dumps(_METRIC_ANSWER).encode()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    @override
    def log_message(self, format: str, *args: object) -> None: ...


@pytest.fixture(name="metric_server")
def fixture_metric_server() -> Iterator[str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _MetricHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()


def _closed_port_url() -> str:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return f"http://127.0.0.1:{sock.getsockname()[1]}"


def _proxy_in_environment(monkeypatch: pytest.MonkeyPatch, proxy_url: str) -> None:
    for name in ("http_proxy", "https_proxy", "all_proxy"):
        monkeypatch.setenv(name, proxy_url)
        monkeypatch.setenv(name.upper(), proxy_url)
    monkeypatch.delenv("no_proxy", raising=False)
    monkeypatch.delenv("NO_PROXY", raising=False)


def _rest_connection(
    perf_data: str,
    *,
    host: str = "127.0.0.1",
    checkmk_url: str = "/heute/check_mk",
    transport: httpx2.AsyncBaseTransport | None = None,
) -> LivestatusConnection:
    site = Mock(spec=SingleSiteConnection)
    site.query.return_value = [[perf_data]]
    return LivestatusConnection(
        host=host,
        timeout=0.5,
        checkmk_url=checkmk_url,
        automation_user="automation",
        automation_secret="secret",
        rest_transport=transport,
        make_site_connection=lambda *_args, **_kwargs: site,
    )


def test_rest_calls_to_the_own_site_go_past_a_proxy_of_the_environment(
    monkeypatch: pytest.MonkeyPatch, metric_server: str
) -> None:
    _proxy_in_environment(monkeypatch, _closed_port_url())
    conn = _rest_connection("load1=1", checkmk_url=f"{metric_server}/heute/check_mk")

    result = asyncio.run(conn.get_metric_history("h", "CPU load", 0, 60))

    assert list(result.series) == ["load1"]


def test_rest_calls_to_another_site_go_through_the_proxy_of_the_environment(
    monkeypatch: pytest.MonkeyPatch, metric_server: str
) -> None:
    _proxy_in_environment(monkeypatch, metric_server)
    conn = _rest_connection(
        "load1=1", host="remote.invalid", checkmk_url="http://remote.invalid/remote/check_mk"
    )

    result = asyncio.run(conn.get_metric_history("h", "CPU load", 0, 60))

    assert list(result.series) == ["load1"]


def test_each_rest_call_ends_at_its_own_deadline() -> None:
    async def _slow_load5(request: httpx2.Request) -> httpx2.Response:
        if b'"load5"' in request.content:
            await asyncio.sleep(60)
        return _metric_answer(request)

    conn = _rest_connection("load1=1 load5=1 load15=1", transport=httpx2.MockTransport(_slow_load5))

    result = asyncio.run(conn.get_metric_history("h", "CPU load", 0, 60))

    assert list(result.series) == ["load1", "load15"]
