#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: Checkmk Enterprise License
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import uuid
from http import HTTPStatus

from cmk.agent_receiver.config import Config
from cmk.relay_protocols.tasks import RelayConfigTask, TaskStatus
from cmk.testlib.agent_receiver.agent_receiver import AgentReceiverClient
from cmk.testlib.agent_receiver.config_file_system import ConfigFolder, create_config_folder
from cmk.testlib.agent_receiver.site_mock import SiteMock
from cmk.testlib.agent_receiver.tasks import get_relay_tasks


def test_activation_performed_by_user_creates_config_tasks_for_each_relay(
    site: SiteMock,
    agent_receiver: AgentReceiverClient,
    site_context: Config,
) -> None:
    # Start AR with two relays configured in the site
    relay_id_a = str(uuid.uuid4())
    relay_id_b = str(uuid.uuid4())
    site.set_scenario([relay_id_a, relay_id_b])

    serial_folder = create_config_folder(site_context.omd_root, [relay_id_a, relay_id_b])

    # Simulate user activation. Call to the endpoint that creates a ActivateConfigTask for each relay
    resp = agent_receiver.activate_config()
    assert resp.status_code == HTTPStatus.OK, resp.text

    # Assert each relay has exactly one pending config task with correct serial
    _assert_single_pending_config_task(
        agent_receiver, serial_folder, relay_id_a, serial_folder.serial
    )
    _assert_single_pending_config_task(
        agent_receiver, serial_folder, relay_id_b, serial_folder.serial
    )


def test_activation_performed_twice_with_same_config(
    site: SiteMock,
    agent_receiver: AgentReceiverClient,
    site_context: Config,
) -> None:
    # Start AR with two relays configured in the site
    relay_id_a = str(uuid.uuid4())
    relay_id_b = str(uuid.uuid4())
    site.set_scenario([relay_id_a, relay_id_b])

    serial_folder = create_config_folder(site_context.omd_root, [relay_id_a, relay_id_b])

    # Simulate user activation. Call to the endpoint that creates a ActivateConfigTask for each relay
    resp = agent_receiver.activate_config()
    assert resp.status_code == HTTPStatus.OK, resp.text

    # Assert each relay has exactly one pending config task with correct serial
    _assert_single_pending_config_task(
        agent_receiver, serial_folder, relay_id_a, serial_folder.serial
    )
    _assert_single_pending_config_task(
        agent_receiver, serial_folder, relay_id_b, serial_folder.serial
    )

    # Simulate second user activation.
    resp = agent_receiver.activate_config()
    assert resp.status_code == HTTPStatus.OK, resp.text

    # Assert each relay has exactly one pending config task with correct serial
    _assert_single_pending_config_task(
        agent_receiver, serial_folder, relay_id_a, serial_folder.serial
    )
    _assert_single_pending_config_task(
        agent_receiver, serial_folder, relay_id_b, serial_folder.serial
    )


def test_activation_with_no_relays(
    site: SiteMock,
    agent_receiver: AgentReceiverClient,
    site_context: Config,
) -> None:
    """Test behavior when no relays are configured."""
    # Start AR with no relays configured in the site
    site.set_scenario([])

    create_config_folder(site_context.omd_root, [])

    # Simulate user activation with no relays
    resp = agent_receiver.activate_config()
    assert resp.status_code == HTTPStatus.OK, resp.text

    # No tasks should be created since there are no relays
    # This test mainly ensures the endpoint doesn't crash with empty relay list


def test_activation_with_mixed_relay_task_states(
    site: SiteMock,
    agent_receiver: AgentReceiverClient,
    site_context: Config,
) -> None:
    """Test activation when some relays already have tasks in different states."""
    # Start AR with two relays configured in the site
    relay_id_a = str(uuid.uuid4())
    relay_id_b = str(uuid.uuid4())
    site.set_scenario([relay_id_a, relay_id_b])

    serial_folder = create_config_folder(site_context.omd_root, [relay_id_a, relay_id_b])

    # First activation - creates pending tasks for both relays
    resp = agent_receiver.activate_config()
    assert resp.status_code == HTTPStatus.OK, resp.text

    # Verify both relays have pending tasks
    _assert_single_pending_config_task(
        agent_receiver, serial_folder, relay_id_a, serial_folder.serial
    )
    _assert_single_pending_config_task(
        agent_receiver, serial_folder, relay_id_b, serial_folder.serial
    )

    # Simulate that relay_a's task completed (this would normally happen via relay processing)
    # For this test, we'll assume the task status changed externally
    # The key test is that activation should still work and not create duplicates
    tasks_a = get_relay_tasks(agent_receiver, relay_id_a)
    _ = agent_receiver.update_task(
        relay_id=relay_id_a,
        task_id=tasks_a.tasks[0].id,
        result_type="OK",
        result_payload="Config update successful message",
    )
    _assert_single_pending_config_task(
        agent_receiver, serial_folder, relay_id_b, serial_folder.serial
    )
    tasks = get_relay_tasks(agent_receiver, relay_id_a)
    assert len(tasks.tasks) == 1
    assert tasks.tasks[0].status == TaskStatus.FINISHED

    # Second activation - should create new pending tasks ONLY for relay_id_a since its previous task is finished
    resp = agent_receiver.activate_config()
    assert resp.status_code == HTTPStatus.OK, resp.text

    _assert_single_pending_config_task(
        agent_receiver, serial_folder, relay_id_b, serial_folder.serial
    )

    tasks_a = get_relay_tasks(agent_receiver, relay_id_a)
    assert len(tasks_a.tasks) == 2
    assert all(
        isinstance(task.spec, RelayConfigTask) and task.spec.serial == serial_folder.serial
        for task in tasks_a.tasks
    )
    task_statuses = [task.status for task in tasks_a.tasks]
    assert TaskStatus.PENDING in task_statuses, f"Expected PENDING status in {task_statuses}"
    assert TaskStatus.FINISHED in task_statuses, f"Expected FINISHED status in {task_statuses}"


def _assert_single_pending_config_task(
    agent_receiver: AgentReceiverClient,
    serial_folder: ConfigFolder,
    relay_id: str,
    expected_serial: str,
) -> None:
    tasks = get_relay_tasks(agent_receiver, relay_id)
    assert len(tasks.tasks) == 1, tasks
    task = tasks.tasks[0]
    assert isinstance(task.spec, RelayConfigTask)
    assert task.spec.serial == expected_serial
    assert task.status == TaskStatus.PENDING
    serial_folder.assert_tar_content(relay_id, task.spec.tar_data)
