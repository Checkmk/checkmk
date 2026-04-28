#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator
from datetime import datetime, timedelta, UTC
from http import HTTPStatus

import pytest
from dateutil.relativedelta import relativedelta

from cmk.agent_receiver.lib.config import Config
from cmk.crypto.certificate import Certificate, CertificatePEM, CertificateWithPrivateKey
from cmk.relay_protocols.relays import RelayRefreshCertResponse
from cmk.testlib.agent_receiver import certs as certslib
from cmk.testlib.agent_receiver.agent_receiver import AgentReceiverClient, register_relay
from cmk.testlib.agent_receiver.relay import random_relay_id
from cmk.testlib.agent_receiver.runner import AgentReceiverRunner
from cmk.testlib.agent_receiver.site_mock import OP, SiteMock, User


@pytest.fixture
def ar_runner(site_context: Config) -> Iterator[AgentReceiverRunner]:
    runner = AgentReceiverRunner(site_context)
    with runner.running():
        runner.wait_for_running()
        yield runner


def test_cert_refresh(
    ar_runner: AgentReceiverRunner,
    site: SiteMock,
    user: User,
) -> None:
    """Verify that a relay can refresh its certificate.

    Test steps:
    1. Register a relay with the agent receiver
    2. Call refresh_cert endpoint for the registered relay
    3. Verify the response status code
    4. Verify the returned client certificate is valid
    """
    relay_id = random_relay_id()
    site.set_scenario([], [(relay_id, OP.ADD)])

    with ar_runner.http_client() as client:
        priv_key, resp = AgentReceiverClient(client, site.site_name, user).register_relay(
            relay_id, "relay1"
        )
        relay_cert = CertificateWithPrivateKey(
            certificate=Certificate.load_pem(CertificatePEM(resp.json()["client_cert"].encode())),
            private_key=priv_key,
        )

    # ClientCertWorker injects the cert CN as INJECTED_UUID_HEADER, authenticating the relay.
    with ar_runner.mtls_client(relay_cert) as client:
        resp = AgentReceiverClient(client, site.site_name, user).refresh_cert(relay_id)

    assert resp.status_code == HTTPStatus.OK
    refresh_response = RelayRefreshCertResponse.model_validate_json(resp.text)
    cert = certslib.read_certificate(refresh_response.client_cert)

    # Verify the certificate CN matches the relay_id
    assert cert.subject.common_name == relay_id

    # Verify that the certificate has correct validity period bounds.
    now = datetime.now(tz=UTC)
    assert cert.not_valid_before <= now
    assert cert.not_valid_before >= now - timedelta(minutes=1)
    assert cert.not_valid_after <= now + relativedelta(months=3)


def test_relay_cert_rotation_rejected_for_wrong_relay(
    ar_runner: AgentReceiverRunner,
    site: SiteMock,
    user: User,
) -> None:
    """Relay cert with CN=A is rejected on relay B's tasks endpoint.

    Test steps:
    1. Register two relays a and b with the agent receiver
    2. use the cert of relay a to refresh the cert of b.
    3. Verify the response status code is FORBIDDEN

    """
    relay_a = random_relay_id()
    relay_b = random_relay_id()
    site.set_scenario([], [(relay_a, OP.ADD), (relay_b, OP.ADD)])

    with ar_runner.http_client() as client:
        priv_key, resp = AgentReceiverClient(client, site.site_name, user).register_relay(
            relay_a, "relaya"
        )
        cert_a = CertificateWithPrivateKey(
            certificate=Certificate.load_pem(CertificatePEM(resp.json()["client_cert"].encode())),
            private_key=priv_key,
        )
        AgentReceiverClient(client, site.site_name, user).register_relay(relay_b, "relayb")

    with ar_runner.mtls_client(cert_a) as client:
        resp = AgentReceiverClient(client, site.site_name, user).refresh_cert(relay_b)

    assert resp.status_code == HTTPStatus.FORBIDDEN


def test_cert_refresh_unknown_relay(
    site: SiteMock,
    agent_receiver: AgentReceiverClient,
) -> None:
    """Verify that cert refresh fails for an unregistered relay.

    Test steps:
    1. Generate a random relay_id (without registering it)
    2. Call refresh_cert endpoint for the unregistered relay
    3. Verify the response returns 404 NOT FOUND
    """
    relay_id = random_relay_id()
    site.set_scenario([], [(relay_id, OP.ADD)])
    resp = agent_receiver.refresh_cert(relay_id)
    assert resp.status_code == HTTPStatus.NOT_FOUND


def test_cert_refresh_api_bad_request(
    site: SiteMock,
    agent_receiver: AgentReceiverClient,
) -> None:
    """Verify that cert refresh handles 400 Bad Request from Checkmk API.

    Test steps:
    1. Register a relay with the agent receiver
    2. Mock the Checkmk API to return 400 Bad Request when checking relay existence
    3. Call refresh_cert endpoint
    4. Verify the response returns 502 Bad Gateway
    """
    relay_id = random_relay_id()
    site.set_scenario([], [(relay_id, OP.ADD)])
    register_relay(agent_receiver, "test_relay", relay_id)

    site.mock_relay_get_error(relay_id, HTTPStatus.BAD_REQUEST, "Bad request from API")

    resp = agent_receiver.refresh_cert(relay_id)
    assert resp.status_code == HTTPStatus.BAD_GATEWAY


def test_cert_refresh_api_internal_error(
    site: SiteMock,
    agent_receiver: AgentReceiverClient,
) -> None:
    """Verify that cert refresh handles 500 Internal Server Error from Checkmk API.

    Test steps:
    1. Register a relay with the agent receiver
    2. Mock the Checkmk API to return 500 Internal Server Error when checking relay existence
    3. Call refresh_cert endpoint
    4. Verify the response returns 502 Bad Gateway
    """
    relay_id = random_relay_id()
    site.set_scenario([], [(relay_id, OP.ADD)])
    register_relay(agent_receiver, "test_relay", relay_id)

    site.mock_relay_get_error(relay_id, HTTPStatus.INTERNAL_SERVER_ERROR, "Internal server error")

    resp = agent_receiver.refresh_cert(relay_id)
    assert resp.status_code == HTTPStatus.BAD_GATEWAY


def test_cert_refresh_api_service_unavailable(
    site: SiteMock,
    agent_receiver: AgentReceiverClient,
) -> None:
    """Verify that cert refresh handles 503 Service Unavailable from Checkmk API.

    Test steps:
    1. Register a relay with the agent receiver
    2. Mock the Checkmk API to return 503 Service Unavailable when checking relay existence
    3. Call refresh_cert endpoint
    4. Verify the response returns 502 Bad Gateway
    """
    relay_id = random_relay_id()
    site.set_scenario([], [(relay_id, OP.ADD)])
    register_relay(agent_receiver, "test_relay", relay_id)

    site.mock_relay_get_error(relay_id, HTTPStatus.SERVICE_UNAVAILABLE, "Service unavailable")

    resp = agent_receiver.refresh_cert(relay_id)
    assert resp.status_code == HTTPStatus.BAD_GATEWAY
