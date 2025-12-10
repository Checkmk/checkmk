#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import dataclasses

from cmk.agent_receiver.relay.api.routers.tasks.libs.config_task_factory import ConfigTaskFactory
from cmk.agent_receiver.relay.api.routers.tasks.libs.retrieve_config_serial import (
    retrieve_config_serial,
)
from cmk.agent_receiver.relay.api.routers.tasks.libs.tasks_repository import (
    RelayTask,
    TasksRepository,
    TaskStatus,
)
from cmk.agent_receiver.relay.lib.shared_types import (
    RelayID,
    TaskID,
)


@dataclasses.dataclass
class GetRelayTasksHandler:
    tasks_repository: TasksRepository
    config_task_factory: ConfigTaskFactory

    def process(
        self, relay_id: RelayID, status: TaskStatus | None, relay_serial: str | None
    ) -> list[RelayTask]:
        current_serial = retrieve_config_serial()
        if relay_serial is not None and relay_serial != current_serial:
            _ = self.config_task_factory.create_for_relay(relay_id)

        return self._get_tasks(relay_id, status)

    def _get_tasks(self, relay_id: RelayID, status: TaskStatus | None) -> list[RelayTask]:
        candidate_tasks = self.tasks_repository.get_tasks(relay_id)
        if not candidate_tasks:
            return []
        if status is None:
            return candidate_tasks
        return [task for task in candidate_tasks if task.status == status]


@dataclasses.dataclass
class GetRelayTaskHandler:
    tasks_repository: TasksRepository

    def process(self, relay_id: RelayID, task_id: TaskID) -> RelayTask:
        return self.tasks_repository.get_task(relay_id, task_id)
