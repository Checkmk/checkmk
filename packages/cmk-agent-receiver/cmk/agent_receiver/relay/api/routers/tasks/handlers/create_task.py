#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import dataclasses

from cmk.agent_receiver.relay.api.routers.tasks.libs.tasks_repository import TasksRepository


@dataclasses.dataclass
class CreateTaskHandler:
    tasks_repository: TasksRepository

    def process(self) -> None:
        pass
