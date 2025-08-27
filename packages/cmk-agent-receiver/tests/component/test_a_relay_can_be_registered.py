#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import uuid

from .test_lib.relay_proxy import RelayProxy
from .test_lib.relays import register_relay


def test_a_relay_can_be_registered(relay_proxy: RelayProxy) -> None:
    """
    Test CT-1. Description:

    POST /relays/{relay_id_A}
    POST /relays/{relay_id_B}
    GET /relays/{relay_id_A}/tasks
    GET /relays/{relay_id_B}/tasks
    """

    relay_id_A = str(uuid.uuid4())
    register_relay(relay_id_A, relay_proxy)

    relay_id_B = str(uuid.uuid4())
    register_relay(relay_id_B, relay_proxy)

    # Verify both relays have tasks queue
    # TODO: Extend the agent receiver test proxy in a next commit
    response_A_tasks = relay_proxy.client.get(
        f"/{relay_proxy.site_name}/agent-receiver/relays/{relay_id_A}/tasks"
    )
    assert response_A_tasks.status_code == 200, (
        f"Failed to get tasks for relay A: {response_A_tasks.text}"
    )

    response_B_tasks = relay_proxy.client.get(
        f"/{relay_proxy.site_name}/agent-receiver/relays/{relay_id_B}/tasks"
    )
    assert response_B_tasks.status_code == 200, (
        f"Failed to get tasks for relay B: {response_B_tasks.text}"
    )
