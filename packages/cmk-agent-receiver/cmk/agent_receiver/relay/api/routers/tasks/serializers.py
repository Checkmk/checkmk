#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import assert_never

from cmk.agent_receiver.relay.api.routers.tasks.libs.tasks_repository import (
    FetchTask,
    RelayConfigTask,
    Task,
)
from cmk.relay_protocols import tasks as tasks_protocol


class TaskResponseSerializer:
    @staticmethod
    def serialize(task: Task) -> tasks_protocol.TaskResponse:
        task_protocol: tasks_protocol.RelayConfigTask | tasks_protocol.FetchAdHocTask | None = None
        match task.payload:
            case RelayConfigTask():
                task_protocol = tasks_protocol.RelayConfigTask(serial=task.payload.serial)
            case FetchTask():
                task_protocol = tasks_protocol.FetchAdHocTask(
                    payload=task.payload.payload,
                    timeout=task.payload.timeout,
                )
            case _:
                assert_never(task)

        return tasks_protocol.TaskResponse(
            id=task.id,
            task=task_protocol,
            status=tasks_protocol.TaskStatus(task.status.value),
            result_type=tasks_protocol.ResultType(task.result_type.value)
            if task.result_type
            else None,
            result_payload=task.result_payload,
            creation_timestamp=task.creation_timestamp,
            update_timestamp=task.update_timestamp,
        )


class TaskListResponseSerializer:
    @staticmethod
    def serialize(task_list: list[Task]) -> tasks_protocol.TaskListResponse:
        return tasks_protocol.TaskListResponse(
            tasks=[TaskResponseSerializer.serialize(task) for task in task_list]
        )
