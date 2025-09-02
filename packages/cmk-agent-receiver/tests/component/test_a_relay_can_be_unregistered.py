#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import uuid
from http import HTTPStatus

from .test_lib.agent_receiver import AgentReceiverClient


def test_a_relay_can_be_unregistered(agent_receiver: AgentReceiverClient) -> None:
    """
    Test CT-2. Description:

    POST /relays/{relay_id_A}
    POST /relays/{relay_id_B}
    DELETE /relays/{relay_id_A}
    GET /relays/{relay_id_B}/tasks
    GET /relays/{relay_id_A}/tasks ⇾ 404
    Wait expiration time
    Check that cleaning expired tasks does not trigger any error regarding missing relay
    """

    relay_id_A = str(uuid.uuid4())
    agent_receiver.register_relay(relay_id_A)

    relay_id_B = str(uuid.uuid4())
    agent_receiver.register_relay(relay_id_B)

    agent_receiver.unregister_relay(relay_id_A)

    # Verify relay B have tasks queue
    resp = agent_receiver.get_all_relay_tasks(relay_id_B)
    assert resp.status_code == HTTPStatus.OK

    resp = agent_receiver.get_all_relay_tasks(relay_id_A)
    assert resp.status_code == HTTPStatus.NOT_FOUND
    assert resp.json()["detail"] == f"Relay with ID {relay_id_A} not found"
