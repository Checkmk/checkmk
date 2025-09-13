#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import dataclasses
from datetime import datetime

from pydantic import SecretStr

from cmk.agent_receiver.log import bound_contextvars
from cmk.agent_receiver.relay.api.routers.tasks.libs.tasks_repository import (
    Task,
    TasksRepository,
    TaskType,
)
from cmk.agent_receiver.relay.lib.relays_repository import RelaysRepository
from cmk.agent_receiver.relay.lib.shared_types import RelayID, RelayNotFoundError, TaskID
from cmk.agent_receiver.relay.lib.site_auth import UserAuth


@dataclasses.dataclass
class CreateTaskHandler:
    tasks_repository: TasksRepository
    relays_repository: RelaysRepository

    def process(
        self, relay_id: RelayID, task_type: TaskType, task_payload: str, authorization: SecretStr
    ) -> TaskID:
        auth = UserAuth(authorization)
        if not self.relays_repository.has_relay(relay_id, auth):
            raise RelayNotFoundError(relay_id)
        now = datetime.now()
        task = Task(
            type=task_type, payload=task_payload, creation_timestamp=now, update_timestamp=now
        )
        with bound_contextvars(task_id=task.id):
            task_created = self.tasks_repository.store_task(relay_id, task)
        return task_created.id
