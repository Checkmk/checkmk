#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import gzip
from base64 import b64encode
from typing import assert_never

from cmk.agent_receiver.relay.api.routers.tasks.libs.tasks_repository import (
    ActiveCheckSpec,
    FetchSpec,
    RelayConfigSpec,
    RelayTask,
)
from cmk.relay_protocols import tasks as tasks_protocol


class TaskResponseSerializer:
    @staticmethod
    def serialize(
        task: RelayTask, config_encoding: tasks_protocol.ConfigEncoding | None = None
    ) -> tasks_protocol.TaskResponse:
        """config_encoding: what the client can unpack; None gets an uncompressed tar."""
        spec: tasks_protocol.TaskResponseSpec | None = None
        match task.spec:
            case RelayConfigSpec():
                spec = tasks_protocol.RelayConfigTask(
                    serial=task.spec.serial.value,
                    # The archive is stored gzip compressed, as current relays want it.
                    # Only relays predating X-CMK-CONFIG-ENCODING get it decompressed.
                    tar_data=b64encode(
                        task.spec.tar_data
                        if config_encoding is tasks_protocol.ConfigEncoding.GZIP
                        else gzip.decompress(task.spec.tar_data)
                    ),
                )
            case FetchSpec():
                spec = tasks_protocol.FetchAdHocTask(
                    payload=task.spec.payload,
                    timeout=task.spec.timeout,
                )
            case ActiveCheckSpec():
                spec = tasks_protocol.AdHocActiveCheckTask(
                    host=task.spec.host,
                    command=task.spec.command,
                    timeout=task.spec.timeout,
                    site_stores=task.spec.site_stores,
                )
            case _:  # pragma: no cover
                assert_never(task)

        return tasks_protocol.TaskResponse(
            id=task.id,
            spec=spec,
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
    def serialize(
        task_list: list[RelayTask], config_encoding: tasks_protocol.ConfigEncoding | None = None
    ) -> tasks_protocol.TaskListResponse:
        return tasks_protocol.TaskListResponse(
            tasks=[TaskResponseSerializer.serialize(task, config_encoding) for task in task_list]
        )
