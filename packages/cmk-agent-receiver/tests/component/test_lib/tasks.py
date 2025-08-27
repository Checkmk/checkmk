#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: Checkmk Enterprise License
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.relay_protocols.tasks import TaskCreateResponse, TaskType

from .relay_proxy import RelayProxy


def push_task(
    relay_proxy: RelayProxy,
    relay_id: str,
    task_type: TaskType,
    task_payload: str,
) -> TaskCreateResponse:
    response = relay_proxy.push_task(
        relay_id=relay_id,
        task_type=task_type,
        task_payload=task_payload,
    )
    assert response.status_code == 200, response.text
    return TaskCreateResponse.model_validate(response.json())
