#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import dataclasses

from cmk.agent_receiver.relay.lib.relays_repository import RelaysRepository
from cmk.relay_protocols.tasks import TaskListResponse, TaskStatus


class RelayNotFoundError(Exception):
    """Exception raised when a relay is not found in the registry."""

    pass


@dataclasses.dataclass
class GetRelayTasksHandler:
    relays_repository: RelaysRepository

    def process(self, relay_id: str, status: TaskStatus | None) -> TaskListResponse:
        return self._get_tasks(relay_id, status)

    def _get_tasks(self, relay_id: str, status: TaskStatus | None) -> TaskListResponse:
        if not self.relays_repository.has_relay(relay_id):
            raise RelayNotFoundError(f"Relay with ID {relay_id} not found")

        tasks = [
            task
            for task in self.relays_repository.get_relay_tasks(relay_id)
            if task.status == status
        ]
        return TaskListResponse(tasks=tasks)
