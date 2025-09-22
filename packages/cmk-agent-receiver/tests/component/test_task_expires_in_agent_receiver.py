#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time

from cmk.relay_protocols.relays import RelayRegistrationResponse
from cmk.relay_protocols.tasks import FetchAdHocTask

from .test_lib.agent_receiver import AgentReceiverClient
from .test_lib.config import create_relay_config as _create_relay_config
from .test_lib.site_mock import OP, SiteMock
from .test_lib.tasks import get_relay_tasks, push_task


def register_relay(ar: AgentReceiverClient, name: str) -> str:
    resp = ar.register_relay(name)
    parsed = RelayRegistrationResponse.model_validate_json(resp.text)
    return parsed.relay_id


def test_task_expires_in_agent_receiver(
    site: SiteMock, agent_receiver: AgentReceiverClient
) -> None:
    """
    1. Configure agent receiver to a short expiration time.
    2. Register relay
    3. Add task
    4. Wait for expiration time
    5. Verify task is no longer present
    """
    # Configure short expiration time
    expiration_time = 1.0
    _create_relay_config(task_ttl=1.0)

    # Step 1: Register relay
    site.set_scenario([], [("Wonderful_relay", OP.ADD)])
    relay_id = register_relay(agent_receiver, "Wonderful_relay")

    # Step 2: Add a task
    task_response = push_task(
        agent_receiver=agent_receiver,
        relay_id=relay_id,
        task=FetchAdHocTask(payload=".."),
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
) -> None:
    """
    Test that verifies that task expiration time resets when a task is updated.

    1. Configure agent receiver to a short expiration time.
    2. Add a task.
    3. Wait until just before the task would expire.
    4. Update the task.
    5. Wait a short time (less than the remaining expiration time).
    6. Verify the task has expired (proving that update did not reset expiration time).
    """
    # Configure short expiration time
    expiration_time = 1.0
    _create_relay_config(task_ttl=1.0)

    # Register relay
    site.set_scenario([], [("Wonderful_relay", OP.ADD)])
    relay_id = register_relay(agent_receiver, "Wonderful_relay")

    # Step 2: Add a task
    task_response = push_task(
        agent_receiver=agent_receiver,
        relay_id=relay_id,
        task=FetchAdHocTask(payload=".."),
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
) -> None:
    """
    Test that verifies that tasks expire regardless of their status.
    """
    # Configure short expiration time
    expiration_time = 1.0
    _create_relay_config(task_ttl=1.0)

    # Register relay
    site.set_scenario([], [("Wonderful_relay", OP.ADD)])
    relay_id = register_relay(agent_receiver, "Wonderful_relay")

    # Step 2: Add a tasks
    task_a_response = push_task(
        agent_receiver=agent_receiver,
        relay_id=relay_id,
        task=FetchAdHocTask(payload="test task A payload"),
    )
    task_a_id = task_a_response.task_id

    task_b_response = push_task(
        agent_receiver=agent_receiver,
        relay_id=relay_id,
        task=FetchAdHocTask(payload="test task B payload"),
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
