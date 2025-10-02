#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_receiver.relay.api.routers.relays.handlers.register_relay import (
    RegisterRelayHandler,
)
from cmk.agent_receiver.relay.lib.site_auth import UserAuth


def test_process_adds_new_relay_id_to_registry(
    register_relay_handler: RegisterRelayHandler,
    test_user: UserAuth,
) -> None:
    relay_id = register_relay_handler.process(test_user.secret, alias="test")
    assert register_relay_handler.relays_repository.has_relay(relay_id, test_user)


def test_process_creates_multiple_relays(
    register_relay_handler: RegisterRelayHandler,
    test_user: UserAuth,
) -> None:
    aliases = ["relay1", "relay2", "relay3", "relay4", "relay5"]
    relay_ids = []

    for alias in aliases:
        relay_id = register_relay_handler.process(test_user.secret, alias=alias)
        relay_ids.append(relay_id)
        assert register_relay_handler.relays_repository.has_relay(relay_id, test_user)

    # Verify all relays are still registered
    for relay_id in relay_ids:
        assert register_relay_handler.relays_repository.has_relay(relay_id, test_user)
