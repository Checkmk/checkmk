#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Component tests for ClientCertWorker verified-uuid injection (CMK-34899).

These run the real Gunicorn worker (ClientCertWorker) over the full TLS stack,
so they exercise the header stripping/injection that a TestClient cannot.
"""

from collections.abc import Iterator
from http import HTTPStatus

import pytest

from cmk.agent_receiver.lib.config import Config
from cmk.agent_receiver.lib.mtls_auth_validator import INJECTED_UUID_HEADER
from cmk.crypto.certificate import Certificate, CertificatePEM, CertificateWithPrivateKey
from cmk.testlib.agent_receiver.agent_receiver import AgentReceiverClient
from cmk.testlib.agent_receiver.relay import random_relay_id
from cmk.testlib.agent_receiver.runner import AgentReceiverRunner
from cmk.testlib.agent_receiver.site_mock import OP, SiteMock, User


@pytest.fixture
def ar_runner(site_context: Config) -> Iterator[AgentReceiverRunner]:
    runner = AgentReceiverRunner(site_context)
    with runner.running():
        runner.wait_for_running()
        yield runner


def test_status_rejects_spoofed_verified_uuid_without_client_cert(
    ar_runner: AgentReceiverRunner,
    site_name: str,
) -> None:
    """A cert-less caller cannot authorize by spoofing the verified-uuid header.

    Send no client certificate but set verified-uuid to the relay id in the URL.
    The worker strips the client-supplied header and injects none (no certificate),
    so the required header is missing and the request is rejected before reaching
    the endpoint.
    """
    relay_id = random_relay_id()
    with ar_runner.http_client() as client:
        resp = client.get(
            f"/{site_name}/relays/{relay_id}/status",
            headers={INJECTED_UUID_HEADER: relay_id},
        )

    assert resp.status_code == HTTPStatus.FORBIDDEN, resp.text
    assert resp.json()["detail"] == "No verified client certificate provided"


def test_status_rejects_no_cert_placeholder_used_as_relay_id(
    ar_runner: AgentReceiverRunner,
    site_name: str,
) -> None:
    """No-certificate placeholder as the relay id.

    The old worker injected "missing: no client certificate provided" as the
    verified-uuid whenever no client certificate was presented. A cert-less
    caller could put that exact string in the URL as the relay id, and the
    injected placeholder would match it, satisfying the mTLS check. The fix
    injects no header at all, so the required header is missing and the request
    is rejected instead of reaching the endpoint.
    """
    encoded_placeholder_relay_id = "missing:%20no%20client%20certificate%20provided"
    with ar_runner.http_client() as client:
        resp = client.get(f"/{site_name}/relays/{encoded_placeholder_relay_id}/status")

    assert resp.status_code == HTTPStatus.FORBIDDEN, resp.text
    assert resp.json()["detail"] == "No verified client certificate provided"


def test_status_authorizes_with_valid_client_cert(
    ar_runner: AgentReceiverRunner,
    site: SiteMock,
    user: User,
    site_name: str,
) -> None:
    """A relay presenting its own certificate is authorized on the same endpoint.

    Proves the rejection above is not blanket denial: the worker derives the
    identity from the verified certificate CN, which matches the relay id in the
    URL, so the request is authorized.
    """
    relay_id = random_relay_id()
    site.set_scenario([], [(relay_id, OP.ADD)])

    with ar_runner.http_client() as client:
        priv_key, resp = AgentReceiverClient(client, site_name, user).register_relay(
            relay_id, "relay1"
        )
        assert resp.status_code == HTTPStatus.OK, resp.text
        relay_cert = CertificateWithPrivateKey(
            certificate=Certificate.load_pem(CertificatePEM(resp.json()["client_cert"].encode())),
            private_key=priv_key,
        )

    site.push_config([relay_id])

    with ar_runner.mtls_client(relay_cert) as client:
        resp = AgentReceiverClient(client, site_name, user).get_relay_status(relay_id)

    assert resp.status_code == HTTPStatus.OK, resp.text


def test_valid_client_cert_ignores_spoofed_verified_uuid_header(
    ar_runner: AgentReceiverRunner,
    site: SiteMock,
    user: User,
    site_name: str,
) -> None:
    """A spoofed verified-uuid header is ignored when a valid certificate is presented.

    The worker strips any client-supplied verified-uuid and injects the CN from the
    verified certificate, so authorization follows the cert -- not the header.
    """
    relay_id = random_relay_id()
    site.set_scenario([], [(relay_id, OP.ADD)])

    with ar_runner.http_client() as client:
        priv_key, resp = AgentReceiverClient(client, site_name, user).register_relay(
            relay_id, "relay1"
        )
        assert resp.status_code == HTTPStatus.OK, resp.text
        relay_cert = CertificateWithPrivateKey(
            certificate=Certificate.load_pem(CertificatePEM(resp.json()["client_cert"].encode())),
            private_key=priv_key,
        )

    site.push_config([relay_id])

    with ar_runner.mtls_client(relay_cert) as client:
        resp = client.get(
            f"/{site_name}/relays/{relay_id}/status",
            headers={INJECTED_UUID_HEADER: random_relay_id()},
        )

    assert resp.status_code == HTTPStatus.OK, resp.text
