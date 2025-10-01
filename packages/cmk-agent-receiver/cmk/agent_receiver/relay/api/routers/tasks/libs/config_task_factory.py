#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import dataclasses
from datetime import datetime, UTC

from cmk.agent_receiver.log import bound_contextvars
from cmk.agent_receiver.relay.api.routers.tasks.libs.retrieve_config_serial import (
    retrieve_config_serial,
)
from cmk.agent_receiver.relay.api.routers.tasks.libs.tasks_repository import (
    RelayConfigSpec,
    RelayTask,
    TasksRepository,
)
from cmk.agent_receiver.relay.lib.relays_repository import RelaysRepository
from cmk.agent_receiver.relay.lib.site_auth import InternalAuth


@dataclasses.dataclass
class ConfigTaskFactory:
    relays_repository: RelaysRepository
    tasks_repository: TasksRepository

    def process(self) -> list[RelayTask]:
        now = datetime.now(UTC)
        created_tasks: list[RelayTask] = []
        auth = InternalAuth()
        serial = retrieve_config_serial()
        relay_config_spec = self._generate_relay_config_spec(serial)
        for relay_id in self.relays_repository.get_all_relay_ids(auth):
            task = RelayTask(spec=relay_config_spec, creation_timestamp=now, update_timestamp=now)
            with bound_contextvars(task_id=task.id):
                self.tasks_repository.store_task(relay_id, task)
                created_tasks.append(task)
        return created_tasks

    def _generate_relay_config_spec(self, serial: str) -> RelayConfigSpec:
        # TODO: Read filesystem and create tar data
        tar_data = ""
        return RelayConfigSpec(serial=serial, tar_data=tar_data)
