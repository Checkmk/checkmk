#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from uuid import uuid4

import httpx
import pytest
from pydantic import SecretStr

from cmk.agent_receiver.lib.certs import serialize_to_pem
from cmk.agent_receiver.relay.api.routers.relays.handlers.register_relay import (
    RegisterRelayHandler,
)
from cmk.agent_receiver.relay.lib.shared_types import RelayID
from cmk.agent_receiver.relay.lib.site_auth import SecretAuth, UnsupportedAuthFormatError
from cmk.relay_protocols.relays import RelayRegistrationRequest
from cmk.testlib.agent_receiver.certs import (
    generate_csr_pair,
)
from cmk.testlib.agent_receiver.relay import site_has_relay


def test_process_adds_new_relay_id_to_registry(
    register_relay_handler: RegisterRelayHandler,
    test_user: SecretAuth,
    site_api_client: httpx.Client,
) -> None:
    relay_id = RelayID(str(uuid4()))
    response = register_relay_handler.process(
        test_user.secret,
        request=RelayRegistrationRequest(
            relay_id=relay_id,
            alias="test",
            csr=_csr(relay_id),
        ),
    )
    assert relay_id == response.relay_id
    assert site_has_relay(site_api_client, RelayID(response.relay_id), test_user)


def test_process_creates_multiple_relays(
    register_relay_handler: RegisterRelayHandler,
    test_user: SecretAuth,
    site_api_client: httpx.Client,
) -> None:
    aliases = ["relay1", "relay2", "relay3"]
    relay_ids = []

    for alias in aliases:
        relay_id = RelayID(str(uuid4()))
        response = register_relay_handler.process(
            authorization=test_user.secret,
            request=RelayRegistrationRequest(
                relay_id=relay_id,
                alias=alias,
                csr=_csr(relay_id),
            ),
        )
        relay_ids.append(relay_id)
        assert relay_id == response.relay_id
        assert site_has_relay(site_api_client, relay_id, test_user)

    # Verify all relays are still registered
    for relay_id in relay_ids:
        assert site_has_relay(site_api_client, relay_id, test_user)


def test_process_adds_relay_with_token_auth(
    register_relay_handler: RegisterRelayHandler,
) -> None:
    token_secret = SecretStr("CMK-TOKEN 0:550e8400-e29b-41d4-a716-446655440000")
    relay_id = RelayID(str(uuid4()))
    response = register_relay_handler.process(
        authorization=token_secret,
        request=RelayRegistrationRequest(
            relay_id=relay_id,
            alias="token-relay",
            csr=_csr(relay_id),
        ),
    )
    assert relay_id == response.relay_id


def test_process_rejects_unknown_auth_format(
    register_relay_handler: RegisterRelayHandler,
) -> None:
    bad_secret = SecretStr("Basic dXNlcjpwYXNz")
    relay_id = RelayID(str(uuid4()))
    with pytest.raises(UnsupportedAuthFormatError):
        register_relay_handler.process(
            authorization=bad_secret,
            request=RelayRegistrationRequest(
                relay_id=relay_id,
                alias="bad-auth-relay",
                csr=_csr(relay_id),
            ),
        )


def _csr(relay_id: RelayID) -> str:
    return serialize_to_pem(generate_csr_pair(cn=relay_id)[1])
