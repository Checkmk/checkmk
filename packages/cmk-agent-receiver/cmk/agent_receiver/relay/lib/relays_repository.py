#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses

from cmk.relay_protocols.tasks import TaskResponse


class RelayNotFoundError(Exception):
    pass


# Note: Consider use Annotated in case we would like to have some pydantic validation
TaskID = str

# Persistence layer is not thread safe yet.
# Note: Since we are using async endpoints in the agent-receiver
# the executions are added as a coroutine to the main async event loop.
# The persistence layer is for now an in memory dict so we won't need
# to make this thread-safe as this should not be accessed by multiple threads
# concurrently.
GLOBAL_RELAYS: dict[TaskID, list[TaskResponse]] = {}


@dataclasses.dataclass
class RelaysRepository:
    def add_relay(self, relay_id: TaskID) -> None:
        if relay_id not in GLOBAL_RELAYS:
            GLOBAL_RELAYS[relay_id] = []

    def list_relays(self) -> list[TaskID]:
        return list(GLOBAL_RELAYS.keys())

    def get_relay_tasks(self, relay_id: TaskID) -> list[TaskResponse]:
        if relay_id not in GLOBAL_RELAYS:
            raise RelayNotFoundError(f"Relay ID {relay_id} not found.")
        return GLOBAL_RELAYS[relay_id]

    def has_relay(self, relay_id: TaskID) -> bool:
        return relay_id in GLOBAL_RELAYS

    def remove_relay(self, relay_id: TaskID) -> None:
        del GLOBAL_RELAYS[relay_id]
