#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses

from cmk.agent_receiver.relay.lib.shared_types import RelayID


class RelayNotFoundError(Exception):
    pass


# Persistence layer is not thread safe yet.
# Note: Since we are using async endpoints in the agent-receiver
# the executions are added as a coroutine to the main async event loop.
# The persistence layer is for now an in memory dict so we won't need
# to make this thread-safe as this should not be accessed by multiple threads
# concurrently.
GLOBAL_RELAYS: set[RelayID] = set()


@dataclasses.dataclass
class RelaysRepository:
    def add_relay(self, relay_id: RelayID) -> None:
        if relay_id not in GLOBAL_RELAYS:
            GLOBAL_RELAYS.add(relay_id)

    def list_relays(self) -> list[RelayID]:
        return list(GLOBAL_RELAYS)

    def has_relay(self, relay_id: RelayID) -> bool:
        return relay_id in GLOBAL_RELAYS

    def remove_relay(self, relay_id: RelayID) -> None:
        GLOBAL_RELAYS.discard(relay_id)
