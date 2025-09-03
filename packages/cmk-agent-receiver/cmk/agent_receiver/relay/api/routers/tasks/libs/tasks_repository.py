#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import NewType

from cmk.agent_receiver.relay.lib.shared_types import RelayID


class TaskStatus(StrEnum):
    PENDING = "PENDING"
    FINISHED = "FINISHED"
    FAILED = "FAILED"


TaskID = NewType("TaskID", str)


class TaskType(StrEnum):
    RELAY_CONFIG = "RELAY_CONFIG"
    FETCH_AD_HOC = "FETCH_AD_HOC"


class ResultType(StrEnum):
    OK = "OK"
    ERROR = "ERROR"


@dataclass(frozen=True)
class Task:
    type: TaskType
    payload: str
    creation_timestamp: datetime
    update_timestamp: datetime
    result_type: ResultType | None = None
    result_payload: str | None = None
    status: TaskStatus = TaskStatus.PENDING
    id: TaskID = dataclasses.field(default_factory=lambda: TaskID(str(uuid.uuid4())))


# Persistence layer is not thread safe yet.
# Note: Since we are using async endpoints in the agent-receiver
# the executions are added as a coroutine to the main async event loop.
# The persistence layer is for now an in memory dict so we won't need
# to make this thread-safe as this should not be accessed by multiple threads
# concurrently.
GLOBAL_TASKS: dict[RelayID, dict[TaskID, Task]] = {}


class TaskNotFoundError(Exception):
    pass


@dataclasses.dataclass
class TasksRepository:
    def get_tasks(self, relay_id: RelayID) -> list[Task]:
        try:
            tasks = GLOBAL_TASKS[relay_id]
        except KeyError:
            logging.warning(f"Relay with ID {relay_id} not found")
            return []
        return list(tasks.values())

    def store_task(self, relay_id: RelayID, task: Task) -> Task:
        if relay_id not in GLOBAL_TASKS:
            GLOBAL_TASKS[relay_id] = {}
        GLOBAL_TASKS[relay_id][task.id] = task
        return task

    def update_task(
        self,
        *,
        relay_id: RelayID,
        task_id: TaskID,
        result_type: ResultType,
        result_payload: str,
        status: TaskStatus,
    ) -> Task:
        try:
            task = GLOBAL_TASKS[relay_id][task_id]
        except KeyError:
            logging.warning(f"Task with ID {task_id} not found")
            raise TaskNotFoundError(task_id)

        new_task = dataclasses.replace(
            task,
            result_type=result_type,
            result_payload=result_payload,
            status=status,
            update_timestamp=datetime.now(),
        )
        GLOBAL_TASKS[relay_id][task_id] = new_task
        return new_task
