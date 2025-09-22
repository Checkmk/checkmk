#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: Checkmk Enterprise License
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from http import HTTPStatus

from cmk.agent_receiver.relay.lib.shared_types import TaskID
from cmk.relay_protocols.tasks import (
    FetchAdHocTask,
    Task,
    TaskCreateResponse,
    TaskListResponse,
    TaskResponse,
)

from .agent_receiver import AgentReceiverClient


def push_task(agent_receiver: AgentReceiverClient, relay_id: str, task: Task) -> TaskCreateResponse:
    """helper to push tasks for a relay.
    It abstracts away the reponses and gives you a reasonable type to work with."""
    response = agent_receiver.push_task(relay_id=relay_id, task=task)
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


def add_tasks(count: int, agent_receiver: AgentReceiverClient, relay_id: str) -> list[TaskID]:
    gen = (
        push_task(
            agent_receiver=agent_receiver,
            relay_id=relay_id,
            task=FetchAdHocTask(payload=f"payload_{i}"),
        )
        for i in range(count)
    )
    result = [TaskID(str(r.task_id)) for r in gen if r is not None]
    assert len(result) == count
    return result


def get_all_tasks(agent_receiver: AgentReceiverClient, relay_id: str) -> list[TaskResponse]:
    return get_relay_tasks(agent_receiver, relay_id).tasks
