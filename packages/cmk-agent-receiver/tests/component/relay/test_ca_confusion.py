#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from datetime import datetime, UTC
from http import HTTPStatus
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from cryptography.x509 import load_pem_x509_certificate

from cmk.agent_receiver.lib.certs import sign_csr
from cmk.agent_receiver.lib.config import Config
from cmk.crypto.certificate import Certificate, CertificateWithPrivateKey
from cmk.testlib.agent_receiver.agent_receiver import AgentReceiverClient
from cmk.testlib.agent_receiver.certs import generate_csr_pair
from cmk.testlib.agent_receiver.relay import random_relay_id
from cmk.testlib.agent_receiver.runner import AgentReceiverRunner
from cmk.testlib.agent_receiver.site_mock import OP, SiteMock, User


@pytest.fixture
def ar_runner(site_context: Config) -> Iterator[AgentReceiverRunner]:
    runner = AgentReceiverRunner(site_context)
    with runner.running():
        runner.wait_for_running()
        yield runner


def _issue_cert(ca_path: Path, uuid: str) -> CertificateWithPrivateKey:
    """Sign a certificate for `uuid` with the CA at `ca_path`, the same way the real
    registration endpoints would for an agent controller or relay with this UUID.

    Loads the CA fresh from disk instead of going through the cached
    `agent_root_ca()`/`relay_root_ca()` so the test process doesn't need
    OMD_ROOT/OMD_SITE pointed at this site.
    """
    private_key, csr = generate_csr_pair(cn=uuid)
    pem_bytes = ca_path.read_bytes()
    ca_key = load_pem_private_key(pem_bytes, None)
    assert isinstance(ca_key, RSAPrivateKey)
    ca_cert = load_pem_x509_certificate(pem_bytes)
    certificate = sign_csr(
        csr.csr, lifetime_in_months=12, keypair=(ca_cert, ca_key), valid_from=datetime.now(UTC)
    )
    return CertificateWithPrivateKey(certificate=Certificate(certificate), private_key=private_key)


def test_agent_cert_rejected_on_relay_endpoint_with_same_uuid(
    ar_runner: AgentReceiverRunner,
    site: SiteMock,
    user: User,
) -> None:
    """A certificate issued for an agent must not authenticate as a relay sharing its UUID.

    The gunicorn workers trust one combined CA bundle (agent CA + relay CA + site CA,
    see agent_cert_store.pem) for the mTLS handshake, and `mtls_authorization_dependency`
    only compares the certificate CN against the UUID in the URL -- it never checks which
    CA signed the certificate. If an agent and a relay end up sharing a UUID, the agent's
    certificate is accepted on relay endpoints.

    Test steps:
    1. Register a relay with a given UUID.
    2. Sign a certificate for the same UUID with the agent CA, as if an agent
       controller had registered with a colliding UUID.
    3. Call a relay endpoint for that UUID using the agent-signed certificate.
    4. The call must be rejected (FORBIDDEN) -- today it is not.
    """
    shared_uuid = random_relay_id()
    site.set_scenario([], [(shared_uuid, OP.ADD)])

    with ar_runner.http_client() as client:
        AgentReceiverClient(client, site.site_name, user).register_relay(
            shared_uuid, "victim-relay"
        )

    agent_cert = _issue_cert(ar_runner.site.agent_ca_path, shared_uuid)

    with ar_runner.mtls_client(agent_cert) as client:
        resp = AgentReceiverClient(client, site.site_name, user).refresh_cert(shared_uuid)

    assert resp.status_code == HTTPStatus.FORBIDDEN


def test_relay_cert_rejected_on_agent_endpoint_with_same_uuid(
    ar_runner: AgentReceiverRunner,
) -> None:
    """A certificate issued for a relay must not authenticate as an agent sharing its UUID.

    Mirrors test_agent_cert_rejected_on_relay_endpoint_with_same_uuid in the other
    direction: a relay-signed certificate must not be accepted on agent-controller
    endpoints (mtls_authorization_dependency("uuid", ...) in agent_receiver/endpoints.py)
    for an agent sharing the relay's UUID.

    Test steps:
    1. Sign a certificate for a UUID with the relay CA, as if a relay had
       registered with that UUID.
    2. Call an agent-controller endpoint for that same UUID using the
       relay-signed certificate.
    3. The call must be rejected (BAD REQUEST) -- today it is not: it is let
       through to the endpoint body, which replies 404 (host not registered)
       instead of rejecting the certificate outright.
    """
    shared_uuid = random_relay_id()
    relay_cert = _issue_cert(ar_runner.site.relay_ca_path, shared_uuid)

    with ar_runner.mtls_client(relay_cert) as client:
        resp = client.get(
            f"/{ar_runner.site.site_name}/agent-receiver/registration_status/{shared_uuid}"
        )

    assert resp.status_code == HTTPStatus.BAD_REQUEST
