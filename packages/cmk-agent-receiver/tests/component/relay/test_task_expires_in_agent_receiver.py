#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pathlib
import time

import pytest

from cmk.agent_receiver.lib.config import Config
from cmk.relay_protocols.tasks import FetchAdHocTask
from cmk.testlib.agent_receiver.agent_receiver import AgentReceiverClient, register_relay
from cmk.testlib.agent_receiver.builder import AgentReceiverConfigBuilder, AgentReceiverSite
from cmk.testlib.agent_receiver.config_file_system import create_config_folder
from cmk.testlib.agent_receiver.relay import random_relay_id
from cmk.testlib.agent_receiver.site_mock import OP, SiteMock
from cmk.testlib.agent_receiver.tasks import get_relay_tasks, push_task
from cmk.testlib.agent_receiver.wiremock import Wiremock


@pytest.fixture()
def site_name() -> str:
    return "my_component_test_site"


@pytest.fixture()
def ar_site(wiremock: Wiremock, tmp_path: pathlib.Path, site_name: str) -> AgentReceiverSite:
    """overwrite global fixture with a task_ttl of 1"""
    return AgentReceiverConfigBuilder(
        omd_root=tmp_path / site_name,
        site_name=site_name,
        apache_address=wiremock.wiremock_hostname,
        apache_port=wiremock.port,
        task_ttl=1.0,
    ).build()


def test_task_expires_in_agent_receiver(
    site: SiteMock,
    agent_receiver: AgentReceiverClient,
    site_context: Config,
    site_name: str,
) -> None:
    """Verify that tasks expire and are automatically removed after the configured TTL (time-to-live) period.

    Test steps:
    1. Register relay and add task
    2. Wait for expiration time
    3. Verify task is no longer present
    """
    expiration_time = 1.0

    # Step 1: Register relay
    relay_id = random_relay_id()
    site.set_scenario([], [(relay_id, OP.ADD)])
    register_relay(agent_receiver, "Wonderful_relay", relay_id)
    cf = create_config_folder(root=site_context.omd_root, relays=[relay_id])
    agent_receiver.set_serial(cf.serial)

    # Step 2: Add a task
    task_response = push_task(
        agent_receiver=agent_receiver,
        relay_id=relay_id,
        spec=FetchAdHocTask(payload=".."),
        site_cn=site_name,
    )

    # Verify task is present initially
    tasks_initial = get_relay_tasks(agent_receiver, relay_id)
    assert len(tasks_initial.tasks) == 1
    assert tasks_initial.tasks[0].id == task_response.task_id

    # Step 3: Wait for expiration time
    time.sleep((expiration_time) + 0.1)  # Adding a small buffer to ensure we are past expiration

    # Step 4: Verify task is no longer present
    tasks_final = get_relay_tasks(agent_receiver, relay_id)
    assert len(tasks_final.tasks) == 0


def test_task_expiration_resets_on_update(
    site: SiteMock,
    agent_receiver: AgentReceiverClient,
    site_context: Config,
    site_name: str,
) -> None:
    """Verify that the task expiration timer is reset when a task is updated, extending its lifetime.

    Test steps:
    1. Add task and wait until half expiration time
    2. Update the task
    3. Verify task remains present after additional half expiration
    4. Verify task expires after full expiration from update
    """
    expiration_time = 1.0

    # Register relay
    relay_id = random_relay_id()
    site.set_scenario([], [(relay_id, OP.ADD)])
    register_relay(agent_receiver, "Wonderful_relay", relay_id)
    cf = create_config_folder(root=site_context.omd_root, relays=[relay_id])
    agent_receiver.set_serial(cf.serial)

    # Step 2: Add a task
    task_response = push_task(
        agent_receiver=agent_receiver,
        relay_id=relay_id,
        spec=FetchAdHocTask(payload=".."),
        site_cn=site_name,
    )
    task_id = task_response.task_id

    # Step 3: Wait half of expiration time
    time.sleep((expiration_time / 2) + 0.1)  # Adding a small buffer to ensure we are past half

    # Step 4: Update the task
    agent_receiver.update_task(
        relay_id=relay_id,
        task_id=task_id,
        result_type="OK",
        result_payload="task updated",
    )

    # Step 5: Wait half of expiration time again
    # If expiration time was reset on update, the task should still be present
    # If expiration time was NOT reset, the task should be gone now
    time.sleep((expiration_time / 2) + 0.1)  # Adding a small buffer to ensure we are past half

    # Step 6: Verify the task is still present
    tasks_response = get_relay_tasks(agent_receiver, relay_id)
    assert len(tasks_response.tasks) == 1, "Task should have not expired and be present"
    assert tasks_response.tasks[0].id == task_response.task_id

    # Step 7: Wait expiration time again
    time.sleep((expiration_time / 2) + 0.1)  # Adding a small buffer to ensure we are past half

    # Step 8: Verify the task has expired
    tasks_response = get_relay_tasks(agent_receiver, relay_id)
    assert len(tasks_response.tasks) == 0, "Task should have expired and not be present"


def test_completed_tasks_expiration(
    site: SiteMock,
    agent_receiver: AgentReceiverClient,
    site_context: Config,
    site_name: str,
) -> None:
    """Verify that tasks expire after their TTL regardless of whether they are pending, finished, or failed.

    Test steps:
    1. Add tasks and update them with different result types
    2. Verify tasks are present initially
    3. Wait for expiration time
    4. Verify all tasks have expired
    """
    expiration_time = 1.0

    # Register relay
    relay_id = random_relay_id()
    site.set_scenario([], [(relay_id, OP.ADD)])
    register_relay(agent_receiver, "Wonderful_relay", relay_id)
    cf = create_config_folder(root=site_context.omd_root, relays=[relay_id])
    agent_receiver.set_serial(cf.serial)

    # Step 2: Add a tasks
    task_a_response = push_task(
        agent_receiver=agent_receiver,
        relay_id=relay_id,
        spec=FetchAdHocTask(payload="test task A payload"),
        site_cn=site_name,
    )
    task_a_id = task_a_response.task_id

    task_b_response = push_task(
        agent_receiver=agent_receiver,
        relay_id=relay_id,
        spec=FetchAdHocTask(payload="test task B payload"),
        site_cn=site_name,
    )
    task_b_id = task_b_response.task_id

    # Step 3: Update the tasks
    agent_receiver.update_task(
        relay_id=relay_id,
        task_id=task_a_id,
        result_type="OK",
        result_payload="task updated",
    )
    agent_receiver.update_task(
        relay_id=relay_id,
        task_id=task_b_id,
        result_type="ERROR",
        result_payload="task updated",
    )
    # Step 4: Verify tasks are present initially
    tasks_response = get_relay_tasks(agent_receiver, relay_id)
    assert len(tasks_response.tasks) == 2, "Both tasks should be present initially"
    assert tasks_response.tasks[0].id in {task_a_id, task_b_id}
    assert tasks_response.tasks[1].id in {task_a_id, task_b_id}

    # Step 5: Wait for expiration time
    time.sleep(expiration_time + 0.1)

    # Step 6: Verify tasks are no longer present
    tasks_response = get_relay_tasks(agent_receiver, relay_id)
    assert len(tasks_response.tasks) == 0, "All tasks should have expired and not be present"
