#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_receiver.relay.api.routers.relays.handlers.unregister_relay import (
    UnregisterRelayHandler,
)
from cmk.agent_receiver.relay.lib.relays_repository import RelaysRepository
from cmk.agent_receiver.relay.lib.shared_types import RelayID, RelayNotFoundError
from cmk.agent_receiver.relay.lib.site_auth import UserAuth


def test_process_removes_relay_id_from_registry(
    relays_repository: RelaysRepository,
    unregister_relay_handler: UnregisterRelayHandler,
    test_user: UserAuth,
) -> None:
    # First add a relay to remove
    relay_id = relays_repository.add_relay(test_user, alias="test-relay")
    assert relays_repository.has_relay(relay_id, test_user)

    # Now unregister it
    unregister_relay_handler.process(relay_id, test_user.secret)
    assert not relays_repository.has_relay(relay_id, test_user)


def test_process_removes_non_existent_relay_id(
    unregister_relay_handler: UnregisterRelayHandler,
    test_user: UserAuth,
) -> None:
    # Try to unregister a non-existent relay
    relay_id = RelayID("non-existent-relay-id")

    assert not unregister_relay_handler.relays_repository.has_relay(relay_id, test_user)
    with pytest.raises(RelayNotFoundError):
        unregister_relay_handler.process(relay_id, test_user.secret)
    assert not unregister_relay_handler.relays_repository.has_relay(relay_id, test_user)
