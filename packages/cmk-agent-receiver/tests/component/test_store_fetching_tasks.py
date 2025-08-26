#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: Checkmk Enterprise License
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from fastapi.testclient import TestClient

from cmk.relay_protocols.tasks import TaskType

from .test_lib.relays import register_relay
from .test_lib.tasks import push_task


def test_store_fetching_tasks(site_name: str, agent_receiver_test_client: TestClient) -> None:
    # TODO: agent_receiver_test_client should come with the site_name ti avoid passing both parameters
    register_relay("relay_id", site_name, agent_receiver_test_client)
    push_task(
        site_name=site_name,
        agent_receiver_test_client=agent_receiver_test_client,
        relay_id="relay_id",
        task_type=TaskType.FETCH_AD_HOC,
        task_payload="any payloa",
    )
    # TODO: Work in progress
