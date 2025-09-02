#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: Checkmk Enterprise License
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import uuid
from http import HTTPStatus

from cmk.relay_protocols.tasks import TaskType

from .test_lib.agent_receiver import AgentReceiverClient
from .test_lib.tasks import get_all_relay_tasks, push_task


def test_store_fetching_task(agent_receiver: AgentReceiverClient) -> None:
    relay_id = str(uuid.uuid4())
    agent_receiver.register_relay(relay_id)

    push_task(
        agent_receiver=agent_receiver,
        relay_id=relay_id,
        task_type=TaskType.FETCH_AD_HOC,
        task_payload="any payload",
    )

    tasks_1 = get_all_relay_tasks(agent_receiver, relay_id)
    assert len(tasks_1.tasks) == 1
    assert tasks_1.tasks[0].type == TaskType.FETCH_AD_HOC
    assert tasks_1.tasks[0].payload == "any payload"


def test_store_fetching_tasks_does_not_affect_other_relays(
    agent_receiver: AgentReceiverClient,
) -> None:
    relay_id_A = str(uuid.uuid4())
    relay_id_B = str(uuid.uuid4())
    agent_receiver.register_relay(relay_id_A)
    agent_receiver.register_relay(relay_id_B)

    push_task(
        agent_receiver=agent_receiver,
        relay_id=relay_id_A,
        task_type=TaskType.FETCH_AD_HOC,
        task_payload="any payload",
    )

    tasks_A = get_all_relay_tasks(agent_receiver, relay_id_A)
    assert len(tasks_A.tasks) == 1
    tasks_B = get_all_relay_tasks(agent_receiver, relay_id_B)
    assert len(tasks_B.tasks) == 0

    push_task(
        agent_receiver=agent_receiver,
        relay_id=relay_id_A,
        task_type=TaskType.FETCH_AD_HOC,
        task_payload="any payload",
    )

    tasks_A = get_all_relay_tasks(agent_receiver, relay_id_A)
    assert len(tasks_A.tasks) == 2
    assert tasks_A.tasks[1].id != tasks_A.tasks[0].id
    tasks_B = get_all_relay_tasks(agent_receiver, relay_id_B)
    assert len(tasks_B.tasks) == 0


def test_store_fetching_task_non_existent_relay(agent_receiver: AgentReceiverClient) -> None:
    relay_id = str(uuid.uuid4())

    response = agent_receiver.push_task(
        relay_id=relay_id,
        task_type=TaskType.FETCH_AD_HOC,
        task_payload="stuff",
    )
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()["detail"] == f"Relay with ID {relay_id} not found"
