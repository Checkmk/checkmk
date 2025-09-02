#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import uuid
from http import HTTPMethod, HTTPStatus

import httpx

from cmk.relay_protocols.tasks import TaskType

from .test_lib.agent_receiver import AgentReceiverClient
from .test_lib.site_mock import SiteMock
from .test_lib.tasks import get_all_relay_tasks, push_task


def test_a_relay_can_be_registered(agent_receiver: AgentReceiverClient) -> None:
    """
    Register a relay and check if we can obtain a list of pending tasks for it.
    """

    relay_id = str(uuid.uuid4())
    resp = agent_receiver.register_relay(relay_id)
    assert resp.status_code == HTTPStatus.OK

    tasks_A = get_all_relay_tasks(agent_receiver, relay_id)
    assert len(tasks_A.tasks) == 0


def test_registering_a_relay_does_not_affect_other_relays(
    agent_receiver: AgentReceiverClient,
) -> None:
    relay_id_A = str(uuid.uuid4())
    agent_receiver.register_relay(relay_id_A)
    push_task(
        agent_receiver=agent_receiver,
        relay_id=relay_id_A,
        task_type=TaskType.FETCH_AD_HOC,
        task_payload="any payload",
    )

    relay_id_B = str(uuid.uuid4())
    agent_receiver.register_relay(relay_id_B)

    tasks_A = get_all_relay_tasks(agent_receiver, relay_id_A)
    assert len(tasks_A.tasks) == 1


def test_contact_site(site: SiteMock) -> None:
    site.wiremock.base_url
    _ = httpx.get(f"{site.wiremock.base_url}/foo")
    reqs = site.wiremock.get_all_url_path_requests("/foo", HTTPMethod.GET)
    assert len(reqs) == 1
