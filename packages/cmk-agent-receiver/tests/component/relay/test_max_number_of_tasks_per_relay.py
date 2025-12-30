#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import uuid
from http import HTTPStatus

from cmk.agent_receiver.lib.config import Config
from cmk.relay_protocols.tasks import FetchAdHocTask
from cmk.testlib.agent_receiver.agent_receiver import AgentReceiverClient
from cmk.testlib.agent_receiver.config import create_relay_config
from cmk.testlib.agent_receiver.config_file_system import create_config_folder
from cmk.testlib.agent_receiver.site_mock import SiteMock
from cmk.testlib.agent_receiver.tasks import add_tasks, get_all_tasks


def test_cannot_push_more_pending_tasks_than_allowed(
    agent_receiver: AgentReceiverClient,
    site: SiteMock,
    site_context: Config,
    site_name: str,
) -> None:
    """Verify that pushing more tasks than the maximum allowed is rejected with a FORBIDDEN status.

    Test steps:
    1. Configure relay with max task limit and push to limit
    2. Attempt to push additional task
    3. Verify request is rejected with FORBIDDEN status
    """
    task_count = 3
    create_relay_config(max_number_of_tasks=task_count)

    relay_id = add_relays(site, 1)[0]
    cf = create_config_folder(root=site_context.omd_root, relays=[relay_id])
    agent_receiver.set_serial(cf.serial)

    # add maximum number of tasks allowed

    task_ids = add_tasks(task_count, agent_receiver, relay_id, site_name)

    # An additional task cannot be pushed

    with agent_receiver.with_client_ip("127.0.0.1"):
        response = agent_receiver.push_task(
            relay_id=relay_id,
            spec=FetchAdHocTask(payload=".."),
            site_cn=site_name,
        )

    assert response.status_code == HTTPStatus.FORBIDDEN, response.text
    assert response.json() == {
        "detail": f"The maximum number of tasks {task_count} has been reached"
    }

    # The list of tasks is unchanged

    current_tasks = {str(t.id) for t in get_all_tasks(agent_receiver, relay_id)}
    assert current_tasks == set(task_ids)


def test_cannot_push_more_tasks_after_marking_a_task_as_finished(
    agent_receiver: AgentReceiverClient,
    site: SiteMock,
    site_context: Config,
    site_name: str,
) -> None:
    """Verify that after marking a task as finished, new tasks can be pushed even when the limit was previously reached.

    Test steps:
    1. Push tasks to limit and mark one as finished
    2. Attempt to push new task
    3. Verify new task is accepted successfully
    """
    task_count = 3
    create_relay_config(max_number_of_tasks=task_count)

    relay_id = add_relays(site, 1)[0]
    cf = create_config_folder(root=site_context.omd_root, relays=[relay_id])
    agent_receiver.set_serial(cf.serial)

    # add maximum number of tasks allowed
    task_id, *_ = add_tasks(task_count, agent_receiver, relay_id, site_name)

    agent_receiver.update_task(
        relay_id=relay_id,
        task_id=task_id,
        result_type="OK",
        result_payload="done",
    )

    with agent_receiver.with_client_ip("127.0.0.1"):
        response = agent_receiver.push_task(
            relay_id=relay_id,
            spec=FetchAdHocTask(payload=".."),
            site_cn=site_name,
        )

    assert response.status_code == HTTPStatus.OK, response.text

    current_tasks = {str(t.id) for t in get_all_tasks(agent_receiver, relay_id)}
    assert len(current_tasks) == task_count + 1


def test_each_relay_has_its_own_limit(
    agent_receiver: AgentReceiverClient, site: SiteMock, site_name: str
) -> None:
    """Verify that each relay has its own independent task limit and filling one relay does not affect others.

    Test steps:
    1. Fill relay A to task limit
    2. Push task to relay B
    3. Verify relay B accepts task despite relay A being full
    """
    task_count = 5
    create_relay_config(max_number_of_tasks=task_count)

    relay_id_A, relay_id_B = add_relays(site, 2)

    # add maximum number of tasks allowed to relay A

    _ = add_tasks(task_count, agent_receiver, relay_id_A, site_name)

    # we should still be able to add tasks to relay B

    with agent_receiver.with_client_ip("127.0.0.1"):
        response = agent_receiver.push_task(
            relay_id=relay_id_B,
            spec=FetchAdHocTask(payload=".."),
            site_cn=site_name,
        )
    assert response.status_code == HTTPStatus.OK, response.text


def add_relays(site: SiteMock, count: int) -> list[str]:
    assert count > 0
    relay_ids = [str(uuid.uuid4()) for _ in range(count)]
    site.set_scenario(relay_ids)
    return relay_ids
