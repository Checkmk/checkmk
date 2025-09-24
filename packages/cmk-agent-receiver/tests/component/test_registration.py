#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from http import HTTPStatus

from cmk.relay_protocols.relays import RelayRegistrationResponse
from cmk.relay_protocols.tasks import FetchAdHocTask

from .test_lib.agent_receiver import AgentReceiverClient
from .test_lib.site_mock import OP, SiteMock
from .test_lib.tasks import get_relay_tasks, push_task


def register_relay(ar: AgentReceiverClient, name: str) -> str:
    resp = ar.register_relay(name)
    parsed = RelayRegistrationResponse.model_validate_json(resp.text)
    return parsed.relay_id


def test_a_relay_can_be_registered(
    site: SiteMock,
    agent_receiver: AgentReceiverClient,
) -> None:
    """
    Register a relay and check if we can obtain a list of pending tasks for it.
    """
    site.set_scenario([], [("relay1", OP.ADD)])
    resp = agent_receiver.register_relay("relay1")
    assert resp.status_code == HTTPStatus.OK
    parsed = RelayRegistrationResponse.model_validate_json(resp.text)
    relay_id = parsed.relay_id

    resp = agent_receiver.get_relay_tasks(relay_id)
    assert resp.status_code == HTTPStatus.OK


def test_registering_a_relay_does_not_affect_other_relays(
    agent_receiver: AgentReceiverClient,
    site: SiteMock,
) -> None:
    site.set_scenario([], [("relay1", OP.ADD), ("relay2", OP.ADD)])
    relay_id_A = register_relay(agent_receiver, "relay1")
    push_task(
        agent_receiver=agent_receiver,
        relay_id=relay_id_A,
        spec=FetchAdHocTask(payload=".."),
    )

    _ = register_relay(agent_receiver, "relay2")

    tasks_A = get_relay_tasks(agent_receiver, relay_id_A)
    assert len(tasks_A.tasks) == 1


def test_a_relay_can_be_unregistered(
    agent_receiver: AgentReceiverClient,
    site: SiteMock,
) -> None:
    site.set_scenario([], [("relay1", OP.ADD), ("relay1", OP.DEL)])
    relay_id = register_relay(agent_receiver, "relay1")
    resp = agent_receiver.get_relay_tasks(relay_id)
    assert resp.status_code == HTTPStatus.OK

    resp = agent_receiver.unregister_relay(relay_id)
    assert resp.status_code == HTTPStatus.OK, resp.text

    # unregistered relay cannot list tasks
    resp = agent_receiver.get_relay_tasks(relay_id)
    assert resp.status_code == HTTPStatus.NOT_FOUND
    assert resp.json()["detail"] == f"Relay with ID '{relay_id}' not found"


def test_unregistering_a_relay_does_not_affect_other_relays(
    agent_receiver: AgentReceiverClient,
    site: SiteMock,
) -> None:
    site.set_scenario([], [("relay1", OP.ADD), ("relay2", OP.ADD), ("relay1", OP.DEL)])
    relay_id_A = register_relay(agent_receiver, "relay1")
    relay_id_B = register_relay(agent_receiver, "relay2")

    agent_receiver.unregister_relay(relay_id_A)

    # Verify relay B have tasks queue
    resp = agent_receiver.get_relay_tasks(relay_id_B)
    assert resp.status_code == HTTPStatus.OK
