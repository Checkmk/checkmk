#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import uuid

from .test_lib.relay_proxy import RelayProxy
from .test_lib.relays import register_relay, unregister_relay
from .test_lib.tasks import get_all_relay_tasks


def test_a_relay_can_be_unregistered(relay_proxy: RelayProxy) -> None:
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
    register_relay(relay_id_A, relay_proxy)

    relay_id_B = str(uuid.uuid4())
    register_relay(relay_id_B, relay_proxy)

    unregister_relay(relay_id_A, relay_proxy)

    # Verify relay B have tasks queue
    tasks_B = get_all_relay_tasks(relay_proxy, relay_id_B)
    assert len(tasks_B.tasks) == 0

    get_all_relay_tasks(
        relay_proxy,
        relay_id_A,
        expected_status_code=404,
        expected_error_message=f"Relay with ID {relay_id_A} not found",
    )
