#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime
from uuid import UUID

from cmk.agent_receiver.relay.api.routers.tasks.libs.tasks_repository import Task
from cmk.relay_protocols.tasks import TaskListResponse, TaskResponse, TaskStatus, TaskType


class TaskResponseSerializer:
    @staticmethod
    def serialize(task: Task) -> TaskResponse:
        # TODO: Multiple fields marked as TODO because the protocol requires
        # them but the resource still don't have a value for them. So, during
        # development let's have some placeholders that will be removed later.
        return TaskResponse(
            id=UUID(task.id),
            type=TaskType(task.type.value),
            status=TaskStatus(task.status.value),
            result_type=None,  # TODO: placeholder
            result_payload=None,  # TODO: placeholder
            creation_timestamp=task.creation_timestamp,
            update_timestamp=datetime.now(),  # TODO: placeholder
            payload=task.payload,
        )


class TaskListResponseSerializer:
    @staticmethod
    def serialize(task_list: list[Task]) -> TaskListResponse:
        return TaskListResponse(
            tasks=[TaskResponseSerializer.serialize(task) for task in task_list]
        )
