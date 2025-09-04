#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from http import HTTPStatus

from cmk.relay_protocols.tasks import TaskType

from .test_lib.agent_receiver import AgentReceiverClient, register_relay
from .test_lib.tasks import get_relay_tasks, push_task


def test_a_relay_can_be_registered(agent_receiver: AgentReceiverClient) -> None:
    """
    Register a relay and check if we can obtain a list of pending tasks for it.
    """
    relay_id = "relay_id"
    resp = agent_receiver.register_relay(relay_id)
    assert resp.status_code == HTTPStatus.OK

    resp = agent_receiver.get_relay_tasks(relay_id)
    assert resp.status_code == HTTPStatus.OK


def test_registering_a_relay_does_not_affect_other_relays(
    agent_receiver: AgentReceiverClient,
) -> None:
    relay_id_A = register_relay(agent_receiver)
    push_task(
        agent_receiver=agent_receiver,
        relay_id=relay_id_A,
        task_type=TaskType.FETCH_AD_HOC,
        task_payload="any payload",
    )

    _ = register_relay(agent_receiver)

    tasks_A = get_relay_tasks(agent_receiver, relay_id_A)
    assert len(tasks_A.tasks) == 1


def test_a_relay_can_be_unregistered(agent_receiver: AgentReceiverClient) -> None:
    relay_id = register_relay(agent_receiver)
    resp = agent_receiver.get_relay_tasks(relay_id)
    assert resp.status_code == HTTPStatus.OK

    resp = agent_receiver.unregister_relay(relay_id)
    assert resp.status_code == HTTPStatus.OK

    # unregistered relay cannot list tasks
    resp = agent_receiver.get_relay_tasks(relay_id)
    assert resp.status_code == HTTPStatus.NOT_FOUND
    assert resp.json()["detail"] == f"Relay with ID {relay_id} not found"


def test_unregistering_a_relay_does_not_affect_other_relays(
    agent_receiver: AgentReceiverClient,
) -> None:
    relay_id_A = register_relay(agent_receiver)
    relay_id_B = register_relay(agent_receiver)

    agent_receiver.unregister_relay(relay_id_A)

    # Verify relay B have tasks queue
    resp = agent_receiver.get_relay_tasks(relay_id_B)
    assert resp.status_code == HTTPStatus.OK
