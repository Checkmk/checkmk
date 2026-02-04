#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Component tests for GET /{relay_id}/status endpoint.

The GET /{relay_id}/status endpoint returns:
- 200: RelayStatusResponse with state (CONFIGURED, PENDING_ACTIVATION, PENDING_DELETION)
- 404: Relay does not exist in CMK API nor in local config
- 502: CMK API returns an error (4xx or 5xx except 404)
"""

from http import HTTPStatus

from cmk.agent_receiver.lib.config import Config
from cmk.relay_protocols.relays import RelayState, RelayStatusResponse
from cmk.testlib.agent_receiver.agent_receiver import AgentReceiverClient, register_relay
from cmk.testlib.agent_receiver.config_file_system import create_config_folder
from cmk.testlib.agent_receiver.relay import random_relay_id
from cmk.testlib.agent_receiver.site_mock import OP, SiteMock


def test_get_relay_status_returns_configured_when_both_api_and_config_exist(
    site: SiteMock,
    agent_receiver: AgentReceiverClient,
    site_context: Config,
) -> None:
    """Verify that GET /{relay_id}/status returns CONFIGURED when relay exists in both API and local config.

    Test steps:
    1. Register a relay with the agent receiver (sets up CMK API to return the relay)
    2. Create local config folder for the relay
    3. Call GET /{relay_id}/status endpoint
    4. Verify the response returns 200 with state CONFIGURED
    """
    relay_id = random_relay_id()
    site.set_scenario([], [(relay_id, OP.ADD)])

    # Register the relay - this sets up CMK API to return the relay
    register_relay(agent_receiver, "test_relay", relay_id)

    # Create local config folder
    _ = create_config_folder(root=site_context.omd_root, relays=[relay_id])

    # Call the endpoint
    resp = agent_receiver.get_relay_status(relay_id)

    assert resp.status_code == HTTPStatus.OK
    response = RelayStatusResponse.model_validate_json(resp.text)
    assert response.relay_id == relay_id
    assert response.state == RelayState.CONFIGURED


def test_get_relay_status_returns_404_when_relay_not_found(
    site: SiteMock,
    agent_receiver: AgentReceiverClient,
) -> None:
    """Verify that GET /{relay_id}/status returns 404 when relay doesn't exist anywhere.

    Test steps:
    1. Generate a random relay_id (without registering it, no local config)
    2. Call GET /{relay_id}/status endpoint
    3. Verify the response returns 404 NOT FOUND
    """
    relay_id = random_relay_id()
    site.set_scenario([])

    resp = agent_receiver.get_relay_status(relay_id)

    assert resp.status_code == HTTPStatus.NOT_FOUND


def test_get_relay_status_returns_pending_activation_when_api_exists_but_no_config(
    site: SiteMock,
    agent_receiver: AgentReceiverClient,
) -> None:
    """Verify that GET /{relay_id}/status returns PENDING_ACTIVATION when relay exists in API but not in local config.

    This scenario occurs when:
    - Relay is registered in CMK (API returns it)
    - But local config hasn't been created yet (activate changes not run)

    Test steps:
    1. Register a relay with the agent receiver
    2. Do NOT create local config folder
    3. Call GET /{relay_id}/status endpoint
    4. Verify the response returns 200 with state PENDING_ACTIVATION
    """
    relay_id = random_relay_id()
    site.set_scenario([], [(relay_id, OP.ADD)])

    # Register the relay - CMK API will return it
    register_relay(agent_receiver, "test_relay", relay_id)

    # Don't create local config folder - simulates pending state

    # Call the endpoint
    resp = agent_receiver.get_relay_status(relay_id)

    assert resp.status_code == HTTPStatus.OK
    response = RelayStatusResponse.model_validate_json(resp.text)
    assert response.relay_id == relay_id
    assert response.state == RelayState.PENDING_ACTIVATION


def test_get_relay_status_returns_pending_deletion_when_config_exists_but_not_in_api(
    site: SiteMock,
    agent_receiver: AgentReceiverClient,
    site_context: Config,
) -> None:
    """Verify that GET /{relay_id}/status returns PENDING_DELETION when config exists but API returns 404.

    This occurs when relay was deleted but config removal hasn't been applied yet.

    Test steps:
    1. Don't register relay in CMK API (so it returns 404)
    2. Create local config folder for the relay
    3. Call GET /{relay_id}/status endpoint
    4. Verify the response returns 200 with state PENDING_DELETION
    """
    relay_id = random_relay_id()
    # Don't add the relay to the scenario - CMK API will return 404
    site.set_scenario([])

    # Create local config folder
    _ = create_config_folder(root=site_context.omd_root, relays=[relay_id])

    # Call the endpoint
    resp = agent_receiver.get_relay_status(relay_id)

    assert resp.status_code == HTTPStatus.OK
    response = RelayStatusResponse.model_validate_json(resp.text)
    assert response.relay_id == relay_id
    assert response.state == RelayState.PENDING_DELETION


def test_get_relay_status_returns_502_on_api_error(
    site: SiteMock,
    agent_receiver: AgentReceiverClient,
    site_context: Config,
) -> None:
    """Verify that GET /{relay_id}/status returns 502 when CMK API returns an error.

    Test steps:
    1. Register a relay with the agent receiver
    2. Create local config folder
    3. Mock the CMK API to return 500 Internal Server Error
    4. Call GET /{relay_id}/status endpoint
    5. Verify the response returns 502 BAD GATEWAY
    """
    relay_id = random_relay_id()
    site.set_scenario([], [(relay_id, OP.ADD)])

    # Register the relay first
    register_relay(agent_receiver, "test_relay", relay_id)

    # Create local config folder
    _ = create_config_folder(root=site_context.omd_root, relays=[relay_id])

    # Mock API error
    site.mock_relay_get_error(relay_id, HTTPStatus.INTERNAL_SERVER_ERROR, "Internal server error")

    resp = agent_receiver.get_relay_status(relay_id)

    assert resp.status_code == HTTPStatus.BAD_GATEWAY


def test_get_relay_status_returns_502_on_bad_request(
    site: SiteMock,
    agent_receiver: AgentReceiverClient,
    site_context: Config,
) -> None:
    """Verify that GET /{relay_id}/status returns 502 when CMK API returns 400 Bad Request.

    Test steps:
    1. Register a relay with the agent receiver
    2. Create local config folder
    3. Mock the CMK API to return 400 Bad Request
    4. Call GET /{relay_id}/status endpoint
    5. Verify the response returns 502 BAD GATEWAY
    """
    relay_id = random_relay_id()
    site.set_scenario([], [(relay_id, OP.ADD)])

    # Register the relay first
    register_relay(agent_receiver, "test_relay", relay_id)

    # Create local config folder
    _ = create_config_folder(root=site_context.omd_root, relays=[relay_id])

    # Mock API error
    site.mock_relay_get_error(relay_id, HTTPStatus.BAD_REQUEST, "Bad request from API")

    resp = agent_receiver.get_relay_status(relay_id)

    assert resp.status_code == HTTPStatus.BAD_GATEWAY
