#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: Checkmk Enterprise License
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime, timedelta, UTC
from http import HTTPStatus

from dateutil.relativedelta import relativedelta

from cmk.relay_protocols.relays import RelayRefreshCertResponse
from cmk.testlib.agent_receiver import certs as certslib
from cmk.testlib.agent_receiver.agent_receiver import AgentReceiverClient, register_relay
from cmk.testlib.agent_receiver.relay import random_relay_id
from cmk.testlib.agent_receiver.site_mock import OP, SiteMock


def test_cert_refresh(
    site: SiteMock,
    agent_receiver: AgentReceiverClient,
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

    # Register the relay first
    register_relay(agent_receiver, "test_relay", relay_id)

    # Refresh the certificate
    resp = agent_receiver.refresh_cert(relay_id)

    # Assert status code
    assert resp.status_code == HTTPStatus.OK

    # Parse the response and verify the client certificate is valid
    refresh_response = RelayRefreshCertResponse.model_validate_json(resp.text)
    cert = certslib.read_certificate(refresh_response.client_cert)

    # Verify the certificate CN matches the relay_id
    assert certslib.check_cn(cert, relay_id)

    # Verify that the certificate has correct validity period bounds.
    now = datetime.now(tz=UTC)
    assert cert.not_valid_before_utc <= now
    assert cert.not_valid_before_utc >= now - timedelta(minutes=1)
    assert cert.not_valid_after_utc <= now + relativedelta(months=3)
