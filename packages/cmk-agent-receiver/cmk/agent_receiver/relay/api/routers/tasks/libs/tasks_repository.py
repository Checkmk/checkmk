#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
import logging
from dataclasses import dataclass
from enum import StrEnum

from cmk.agent_receiver.relay.lib.shared_types import RelayID


class TaskStatus(StrEnum):
    PENDING = "PENDING"
    FINISHED = "FINISHED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class Task:
    id: str
    status: TaskStatus
    version: int = 1


# Persistence layer is not thread safe yet.
# Note: Since we are using async endpoints in the agent-receiver
# the executions are added as a coroutine to the main async event loop.
# The persistence layer is for now an in memory dict so we won't need
# to make this thread-safe as this should not be accessed by multiple threads
# concurrently.
GLOBAL_TASKS: dict[RelayID, list[Task]] = {}


@dataclasses.dataclass
class TasksRepository:
    def get_tasks(self, relay_id: RelayID) -> list[Task]:
        try:
            tasks = GLOBAL_TASKS[relay_id]
        except KeyError:
            logging.warning(f"Relay with ID {relay_id} not found")
            return []
        return tasks
