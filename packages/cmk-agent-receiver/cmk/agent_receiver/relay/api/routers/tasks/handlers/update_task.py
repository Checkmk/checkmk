#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import dataclasses

from pydantic import SecretStr

from cmk.agent_receiver.relay.api.routers.tasks.libs.tasks_repository import (
    ResultType,
    Task,
    TasksRepository,
    TaskStatus,
)
from cmk.agent_receiver.relay.api.routers.tasks.libs.tasks_repository import (
    TaskNotFoundError as RepositoryTaskNotFoundError,
)
from cmk.agent_receiver.relay.lib.relays_repository import RelaysRepository
from cmk.agent_receiver.relay.lib.shared_types import RelayID, TaskID


class RelayNotFoundError(Exception):
    pass


class TaskNotFoundError(Exception):
    pass


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
        authorization: SecretStr,
    ) -> Task:
        if not self.relays_repository.has_relay(relay_id, authorization):
            raise RelayNotFoundError(f"Relay with ID {relay_id} does not exist")
        return self._update_task(relay_id, task_id, result_type, result_payload)

    def _update_task(
        self, relay_id: RelayID, task_id: TaskID, result_type: ResultType, result_payload: str
    ) -> Task:
        try:
            task = self.tasks_repository.update_task(
                relay_id=relay_id,
                task_id=task_id,
                result_type=result_type,
                result_payload=result_payload,
                status=TaskStatus.FINISHED if result_type == ResultType.OK else TaskStatus.FAILED,
            )
        except RepositoryTaskNotFoundError as e:
            raise TaskNotFoundError(f"Task with ID {task_id} does not exist") from e
        return task
