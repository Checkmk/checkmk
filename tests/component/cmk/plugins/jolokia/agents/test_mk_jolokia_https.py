#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Component tests: mk_jolokia talking HTTPS to an in-process Jolokia stand-in"""

# Agent plugins still need to support Python 3.4
# ruff: noqa: UP035  # PEP 585 (Type Hinting Generics In Standard Collections) is a Python 3.9 feature

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"

import http.server
import json
import os
import ssl
import threading
from typing import Iterator

import pytest
import requests
from _pytest.monkeypatch import MonkeyPatch

from cmk.plugins.jolokia.agents import mk_jolokia

# The datasets hold a server certificate signed by a test CA absent from the requests CA bundle,
# so the connection succeeds only when the plug-in also consults the OS trust store.

_CERT_DIR = os.path.join(os.path.dirname(__file__), "datasets", "mk_jolokia")
_CA_FILE = os.path.join(_CERT_DIR, "ca.pem")
_SERVER_CERT_FILE = os.path.join(_CERT_DIR, "server-cert.pem")
_SERVER_KEY_FILE = os.path.join(_CERT_DIR, "server-key.pem")

_JOLOKIA_RESPONSE = {"status": 200, "value": 42}


class _JolokiaHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        self.rfile.read(int(self.headers.get("Content-Length", 0)))
        body = json.dumps(_JOLOKIA_RESPONSE).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@pytest.fixture(name="https_port")
def fixture_https_port() -> Iterator[int]:
    server = http.server.HTTPServer(("127.0.0.1", 0), _JolokiaHandler)
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(_SERVER_CERT_FILE, _SERVER_KEY_FILE)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()


@pytest.fixture(name="os_trust_store_with_test_ca")
def fixture_os_trust_store_with_test_ca(monkeypatch: MonkeyPatch) -> None:
    """Emulate a monitored host whose OS trust store contains the test CA"""

    def load_default_certs(self, _purpose=ssl.Purpose.SERVER_AUTH):
        self.load_verify_locations(cafile=_CA_FILE)

    monkeypatch.setattr(ssl.SSLContext, "load_default_certs", load_default_certs)


def _https_instance(port, verify):
    # type: (int, object) -> mk_jolokia.JolokiaInstance
    config = mk_jolokia.get_default_config_dict()
    config.update({"protocol": "https", "server": "localhost", "port": port, "mode": None})
    config["verify"] = verify
    return mk_jolokia.JolokiaInstance(config, mk_jolokia.USER_AGENT)


@pytest.mark.usefixtures("os_trust_store_with_test_ca")
def test_https_trusts_os_certificate_store(https_port: int, monkeypatch: MonkeyPatch) -> None:
    """Regression test for SUP-30550: a CA in the OS trust store must verify the server cert."""
    monkeypatch.setattr(mk_jolokia, "DEBUG", 1)  # surface the real error instead of SkipInstance
    instance = _https_instance(https_port, verify=None)  # normalizes to the default: verify=True

    assert instance.post({"type": "version"}) == _JOLOKIA_RESPONSE


def test_https_rejects_certificate_from_unknown_ca(
    https_port: int, monkeypatch: MonkeyPatch
) -> None:
    """Trusting the OS store must not disable verification altogether"""
    monkeypatch.setattr(mk_jolokia, "DEBUG", 1)
    instance = _https_instance(https_port, verify=None)

    with pytest.raises(requests.exceptions.SSLError):
        instance.post({"type": "version"})
