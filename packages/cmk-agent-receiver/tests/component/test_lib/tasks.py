#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: Checkmk Enterprise License
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from http import HTTPStatus

from cmk.relay_protocols.tasks import TaskCreateResponse, TaskListResponse, TaskType

from .agent_receiver import AgentReceiverClient


def push_task(
    agent_receiver: AgentReceiverClient, relay_id: str, task_type: TaskType, task_payload: str
) -> TaskCreateResponse:
    """helper to push tasks for a relay.
    It abstracts away the reponses and gives you a reasonable type to work with."""
    response = agent_receiver.push_task(
        relay_id=relay_id,
        task_type=task_type,
        task_payload=task_payload,
    )
    assert response.status_code == HTTPStatus.OK, response.text
    return TaskCreateResponse.model_validate(response.json())


def get_relay_tasks(
    agent_receiver: AgentReceiverClient, relay_id: str, status: str | None = None
) -> TaskListResponse:
    """helper to push tasks for a relay.
    It abstracts away the reponses and gives you a reasonable type to work with."""
    response = agent_receiver.get_relay_tasks(relay_id, status=status)
    assert response.status_code == HTTPStatus.OK, response.text
    return TaskListResponse.model_validate(response.json())
