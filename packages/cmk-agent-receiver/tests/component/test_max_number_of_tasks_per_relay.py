#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: Checkmk Enterprise License
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import uuid
from http import HTTPStatus

from cmk.relay_protocols.tasks import TaskType

from .test_lib.agent_receiver import AgentReceiverClient
from .test_lib.config import create_relay_config
from .test_lib.site_mock import SiteMock
from .test_lib.tasks import add_tasks, get_all_tasks


def test_cannot_push_more_tasks_than_allowed(
    agent_receiver: AgentReceiverClient, site: SiteMock
) -> None:
    """
    We should not be able to push more tasks than maximum allowed.
    """
    task_count = 3
    create_relay_config(max_number_of_tasks=task_count)

    relay_id = add_relays(site, 1)[0]

    # add maximum number of tasks allowed

    task_ids = add_tasks(task_count, agent_receiver, relay_id)

    # An additional task cannot be pushed

    response = agent_receiver.push_task(
        relay_id=relay_id,
        task_type=TaskType.FETCH_AD_HOC,
        task_payload="payload",
    )

    assert response.status_code == HTTPStatus.FORBIDDEN, response.text
    assert response.json() == {
        "detail": f"The maximum number of tasks {task_count} has been reached"
    }

    # The list of tasks is unchanged

    current_tasks = {str(t.id) for t in get_all_tasks(agent_receiver, relay_id)}
    assert current_tasks == set(task_ids)


def test_each_relay_has_its_own_limit(agent_receiver: AgentReceiverClient, site: SiteMock) -> None:
    """
    Other relays should not be affected when one relay is "full".
    """
    task_count = 5
    create_relay_config(max_number_of_tasks=task_count)

    relay_id_A, relay_id_B = add_relays(site, 2)

    # add maximum number of tasks allowed to relay A

    _ = add_tasks(task_count, agent_receiver, relay_id_A)

    # we should still be able to add tasks to relay B

    response = agent_receiver.push_task(
        relay_id=relay_id_B,
        task_type=TaskType.FETCH_AD_HOC,
        task_payload="payload",
    )
    assert response.status_code == HTTPStatus.OK, response.text


def add_relays(site: SiteMock, count: int) -> list[str]:
    assert count > 0
    relay_ids = [str(uuid.uuid4()) for _ in range(count)]
    site.set_scenario(relay_ids)
    return relay_ids
