#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import dataclasses

from cmk.agent_receiver.relay.api.routers.tasks.libs.config_task_factory import ConfigTaskFactory
from cmk.agent_receiver.relay.api.routers.tasks.libs.tasks_repository import RelayTask

# TODO Question: should we use ConfigTaskFactory directly instead of ActivateConfigHandler?


@dataclasses.dataclass
class ActivateConfigHandler:
    config_task_factory: ConfigTaskFactory

    def process(self) -> list[RelayTask]:
        return self.config_task_factory.process()
