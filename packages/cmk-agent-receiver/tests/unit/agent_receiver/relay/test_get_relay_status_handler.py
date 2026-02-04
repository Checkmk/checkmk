#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Unit tests for GetRelayStatusHandler.

The GET /{relay_id}/status endpoint returns:
- 200: RelayStatusResponse with state (CONFIGURED, PENDING_ACTIVATION, PENDING_DELETION)
- 404: Relay does not exist in CMK API nor in local config
"""

from uuid import uuid4

import pytest

from cmk.agent_receiver.lib.certs import serialize_to_pem
from cmk.agent_receiver.lib.config import Config
from cmk.agent_receiver.relay.api.routers.relays.handlers.register_relay import (
    GetRelayStatusHandler,
    RegisterRelayHandler,
)
from cmk.agent_receiver.relay.lib.relays_repository import RelayNotFoundError
from cmk.agent_receiver.relay.lib.shared_types import RelayID
from cmk.agent_receiver.relay.lib.site_auth import UserAuth
from cmk.relay_protocols.relays import RelayRegistrationRequest, RelayState
from cmk.testlib.agent_receiver.certs import generate_csr_pair


def test_get_relay_status_returns_configured_when_both_api_and_config_exist(
    get_relay_status_handler: GetRelayStatusHandler,
    register_relay_handler: RegisterRelayHandler,
    test_user: UserAuth,
    site_context: Config,
) -> None:
    """Test that get_relay_status returns CONFIGURED when relay exists in both API and local config."""
    relay_id = RelayID(str(uuid4()))

    # Register the relay - this adds it to the mock CMK API
    register_relay_handler.process(
        test_user.secret,
        request=RelayRegistrationRequest(
            relay_id=relay_id,
            alias="test-alias",
            csr=_csr(relay_id),
        ),
    )

    # Create local config folder
    relay_config_dir = site_context.helper_config_dir / "latest/relays" / relay_id
    relay_config_dir.mkdir(parents=True, exist_ok=True)

    # Act
    response = get_relay_status_handler.process(relay_id=relay_id)

    # Assert
    assert response.relay_id == relay_id
    assert response.state == RelayState.CONFIGURED


def test_get_relay_status_raises_not_found_when_relay_not_in_api_nor_config(
    get_relay_status_handler: GetRelayStatusHandler,
) -> None:
    """Test that get_relay_status raises RelayNotFoundError when relay doesn't exist anywhere."""
    relay_id = RelayID(str(uuid4()))

    # No registration in API, no local config - truly not found
    with pytest.raises(RelayNotFoundError):
        get_relay_status_handler.process(relay_id=relay_id)


def test_get_relay_status_returns_pending_activation_when_api_exists_but_no_local_config(
    get_relay_status_handler: GetRelayStatusHandler,
    register_relay_handler: RegisterRelayHandler,
    test_user: UserAuth,
) -> None:
    """Test that get_relay_status returns PENDING_ACTIVATION when relay exists in API but not in local config.

    This scenario occurs when:
    - Relay is registered in CMK (API returns it)
    - But local config hasn't been created yet (activate changes not run)
    """
    relay_id = RelayID(str(uuid4()))

    # Register in CMK API
    register_relay_handler.process(
        test_user.secret,
        request=RelayRegistrationRequest(
            relay_id=relay_id,
            alias="test-alias",
            csr=_csr(relay_id),
        ),
    )

    # Don't create local config folder - simulates pending state

    response = get_relay_status_handler.process(relay_id=relay_id)

    assert response.relay_id == relay_id
    assert response.state == RelayState.PENDING_ACTIVATION


def test_get_relay_status_returns_pending_deletion_when_config_exists_but_not_in_api(
    get_relay_status_handler: GetRelayStatusHandler,
    site_context: Config,
) -> None:
    """Test that get_relay_status returns PENDING_DELETION when config exists but API returns 404.

    This occurs when relay was deleted but config removal hasn't been applied yet.
    """
    relay_id = RelayID(str(uuid4()))

    # Don't register in CMK API (so GET will return 404)
    # But create the local config folder
    relay_config_dir = site_context.helper_config_dir / "latest/relays" / relay_id
    relay_config_dir.mkdir(parents=True, exist_ok=True)

    response = get_relay_status_handler.process(relay_id=relay_id)

    assert response.relay_id == relay_id
    assert response.state == RelayState.PENDING_DELETION


def _csr(relay_id: RelayID) -> str:
    return serialize_to_pem(generate_csr_pair(cn=relay_id)[1])
