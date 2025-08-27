#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: Checkmk Enterprise License
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from starlette.status import HTTP_200_OK

from cmk.relay_protocols.tasks import TaskCreateResponse, TaskListResponse, TaskType

from .relay_proxy import RelayProxy


def push_task(
    relay_proxy: RelayProxy,
    relay_id: str,
    task_type: TaskType,
    task_payload: str,
    expected_status_code: int = HTTP_200_OK,
    expected_error_message: str | None = None,
) -> TaskCreateResponse | None:
    response = relay_proxy.push_task(
        relay_id=relay_id,
        task_type=task_type,
        task_payload=task_payload,
    )
    assert response.status_code == expected_status_code, response.text
    if expected_error_message:
        assert expected_error_message in response.text, response.text
        return None
    return TaskCreateResponse.model_validate(response.json())


def get_all_relay_tasks(
    relay_proxy: RelayProxy,
    relay_id: str,
    expected_status_code: int = HTTP_200_OK,
    expected_error_message: str | None = None,
) -> TaskListResponse:
    response = relay_proxy.get_all_relay_tasks(relay_id)
    assert response.status_code == expected_status_code, response.text
    if expected_error_message:
        assert expected_error_message in response.text, response.text
        return TaskListResponse(tasks=[])
    return TaskListResponse.model_validate(response.json())
