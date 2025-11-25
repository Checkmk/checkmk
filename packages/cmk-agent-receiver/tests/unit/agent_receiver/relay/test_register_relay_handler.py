#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from uuid import uuid4

import pytest

from cmk.agent_receiver.lib.certs import serialize_to_pem
from cmk.agent_receiver.relay.api.routers.relays.handlers.register_relay import (
    RegisterRelayHandler,
)
from cmk.agent_receiver.relay.lib.shared_types import RelayID
from cmk.agent_receiver.relay.lib.site_auth import UserAuth
from cmk.relay_protocols.relays import RelayRegistrationRequest
from cmk.testlib.agent_receiver.certs import (
    check_certificate_against_private_key,
    check_cn,
    generate_csr_pair,
    read_certificate,
)
from cmk.testlib.agent_receiver.relay import random_relay_id


def test_process_adds_new_relay_id_to_registry(
    register_relay_handler: RegisterRelayHandler,
    test_user: UserAuth,
) -> None:
    relay_id = RelayID(str(uuid4()))
    response = register_relay_handler.process(
        test_user.secret,
        request=RelayRegistrationRequest(
            relay_id=relay_id,
            alias="test",
            csr=serialize_to_pem(generate_csr_pair(cn=relay_id)[1]),
        ),
    )
    assert relay_id == response.relay_id
    assert register_relay_handler.relays_repository.has_relay(RelayID(response.relay_id), test_user)


def test_process_creates_valid_certificate(
    register_relay_handler: RegisterRelayHandler,
    test_user: UserAuth,
) -> None:
    relay_id = random_relay_id()
    private_key, csr = generate_csr_pair(cn=relay_id)
    response = register_relay_handler.process(
        test_user.secret,
        request=RelayRegistrationRequest(
            relay_id=relay_id,
            alias="test",
            csr=serialize_to_pem(csr),
        ),
    )
    cert = read_certificate(response.client_cert)
    assert check_cn(cert, relay_id)
    check_certificate_against_private_key(cert, private_key)


def test_process_validates_csr(
    register_relay_handler: RegisterRelayHandler,
    test_user: UserAuth,
) -> None:
    relay_id = random_relay_id()
    _, csr = generate_csr_pair(cn=random_relay_id())
    with pytest.raises(ValueError):
        register_relay_handler.process(
            test_user.secret,
            request=RelayRegistrationRequest(
                relay_id=relay_id,
                alias="test",
                csr=serialize_to_pem(csr),
            ),
        )


def test_process_creates_multiple_relays(
    register_relay_handler: RegisterRelayHandler,
    test_user: UserAuth,
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
                csr=serialize_to_pem(generate_csr_pair(cn=relay_id)[1]),
            ),
        )
        relay_ids.append(relay_id)
        assert relay_id == response.relay_id
        assert register_relay_handler.relays_repository.has_relay(relay_id, test_user)

    # Verify all relays are still registered
    for relay_id in relay_ids:
        assert register_relay_handler.relays_repository.has_relay(relay_id, test_user)
