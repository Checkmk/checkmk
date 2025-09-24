#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import dataclasses

from cmk.agent_receiver.relay.api.routers.tasks.libs.tasks_repository import (
    RelayTask,
    ResultType,
    TasksRepository,
    TaskStatus,
)
from cmk.agent_receiver.relay.lib.relays_repository import RelaysRepository
from cmk.agent_receiver.relay.lib.shared_types import (
    RelayID,
    RelayNotFoundError,
    TaskID,
)
from cmk.agent_receiver.relay.lib.site_auth import InternalAuth


@dataclasses.dataclass
class UpdateTaskHandler:
    tasks_repository: TasksRepository
    relays_repository: RelaysRepository

    def process(
        self,
        relay_id: RelayID,
        task_id: TaskID,
        result_type: ResultType,
        result_payload: str,
    ) -> RelayTask:
        auth = InternalAuth()
        if not self.relays_repository.has_relay(relay_id, auth):
            raise RelayNotFoundError(relay_id)
        return self._update_task(relay_id, task_id, result_type, result_payload)

    def _update_task(
        self, relay_id: RelayID, task_id: TaskID, result_type: ResultType, result_payload: str
    ) -> RelayTask:
        task = self.tasks_repository.update_task(
            relay_id=relay_id,
            task_id=task_id,
            result_type=result_type,
            result_payload=result_payload,
            status=TaskStatus.FINISHED if result_type == ResultType.OK else TaskStatus.FAILED,
        )
        return task
