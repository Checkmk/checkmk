#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import dataclasses

from cmk.agent_receiver.relay.api.routers.tasks.libs import tasks_repository
from cmk.agent_receiver.relay.lib import relays_repository
from cmk.relay_protocols.tasks import TaskListResponse, TaskStatus


class RelayNotFoundError(Exception):
    """Exception raised when a relay is not found in the registry."""

    pass


@dataclasses.dataclass
class GetRelayTasksHandler:
    tasks_repository: tasks_repository.TasksRepository
    relay_repository: relays_repository.RelaysRepository

    def process(self, relay_id: str, status: TaskStatus | None) -> TaskListResponse:
        return self._get_tasks(relay_id, status)

    def _get_tasks(self, relay_id: str, status: TaskStatus | None) -> TaskListResponse:
        if not self.relay_repository.has_relay(relay_id):
            raise RelayNotFoundError(f"Relay with ID {relay_id} not found")

        candidate_tasks = self.tasks_repository.get_tasks(relay_id)
        if not candidate_tasks:
            return TaskListResponse(tasks=[])
        tasks = [task for task in candidate_tasks if task.status == status]
        return TaskListResponse(tasks=tasks)
