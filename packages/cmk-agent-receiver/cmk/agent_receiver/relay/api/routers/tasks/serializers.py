#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_receiver.relay.api.routers.tasks.libs.tasks_repository import Task
from cmk.relay_protocols.tasks import (
    ResultType,
    TaskListResponse,
    TaskResponse,
    TaskStatus,
    TaskType,
)


class TaskResponseSerializer:
    @staticmethod
    def serialize(task: Task) -> TaskResponse:
        return TaskResponse(
            id=task.id,
            type=TaskType(task.type.value),
            status=TaskStatus(task.status.value),
            result_type=ResultType(task.result_type.value) if task.result_type else None,
            result_payload=task.result_payload,
            creation_timestamp=task.creation_timestamp,
            update_timestamp=task.update_timestamp,
            payload=task.payload,
        )


class TaskListResponseSerializer:
    @staticmethod
    def serialize(task_list: list[Task]) -> TaskListResponse:
        return TaskListResponse(
            tasks=[TaskResponseSerializer.serialize(task) for task in task_list]
        )
