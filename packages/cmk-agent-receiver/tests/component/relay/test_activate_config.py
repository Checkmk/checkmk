#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: Checkmk Enterprise License
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import uuid
from http import HTTPStatus

import httpx
import pytest

from cmk.agent_receiver.lib.config import Config
from cmk.agent_receiver.relay.lib.shared_types import Serial
from cmk.relay_protocols.tasks import RelayConfigTask, TaskResponse, TaskStatus
from cmk.testlib.agent_receiver.agent_receiver import AgentReceiverClient
from cmk.testlib.agent_receiver.config_file_system import ConfigFolder, create_config_folder
from cmk.testlib.agent_receiver.site_mock import (
    OP,
    SiteMock,
    User,
)
from cmk.testlib.agent_receiver.tasks import get_relay_tasks


@pytest.fixture
def site_client(site: SiteMock, user: User) -> httpx.Client:
    return httpx.Client(
        base_url=site.base_url,
        headers={
            "Content-Type": "application/json",
            "Authorization": user.bearer,
        },
    )


def test_activation_performed_by_user_creates_config_tasks_for_each_relay(
    site: SiteMock,
    agent_receiver: AgentReceiverClient,
    site_context: Config,
    site_name: str,
) -> None:
    """Verify that user-triggered config activation creates a relay config task for each configured relay.

    Test steps:
    1. Configure agent receiver with two relays
    2. Perform config activation
    3. Verify each relay has exactly one pending config task
    """
    # Start AR with two relays configured in the site
    relay_id_a = str(uuid.uuid4())
    relay_id_b = str(uuid.uuid4())
    site.set_scenario([relay_id_a, relay_id_b])

    serial_folder = create_config_folder(site_context.omd_root, [relay_id_a, relay_id_b])
    agent_receiver.set_serial(serial_folder.serial)

    # Simulate user activation. Call to the endpoint that creates a ActivateConfigTask for each relay
    with agent_receiver.with_client_ip("127.0.0.1"):
        resp = agent_receiver.activate_config(site_cn=site_name)
    assert resp.status_code == HTTPStatus.OK, resp.text

    # Assert each relay has exactly one pending config task with correct serial
    _assert_single_pending_config_task(agent_receiver, serial_folder, relay_id_a)
    _assert_single_pending_config_task(agent_receiver, serial_folder, relay_id_b)


def test_activation_performed_twice_with_same_config(
    site: SiteMock,
    agent_receiver: AgentReceiverClient,
    site_context: Config,
    site_name: str,
) -> None:
    """Verify that performing config activation twice with the same configuration does not create duplicate tasks.

    Test steps:
    1. Configure agent receiver and perform first activation
    2. Perform second activation with same config
    3. Verify each relay still has only one pending config task
    """
    # Start AR with two relays configured in the site
    relay_id_a = str(uuid.uuid4())
    relay_id_b = str(uuid.uuid4())
    site.set_scenario([relay_id_a, relay_id_b])

    serial_folder = create_config_folder(site_context.omd_root, [relay_id_a, relay_id_b])
    agent_receiver.set_serial(serial_folder.serial)

    # Simulate user activation. Call to the endpoint that creates a ActivateConfigTask for each relay
    with agent_receiver.with_client_ip("127.0.0.1"):
        resp = agent_receiver.activate_config(site_cn=site_name)
    assert resp.status_code == HTTPStatus.OK, resp.text

    # Assert each relay has exactly one pending config task with correct serial
    _assert_single_pending_config_task(agent_receiver, serial_folder, relay_id_a)
    _assert_single_pending_config_task(agent_receiver, serial_folder, relay_id_b)

    # Simulate second user activation.
    with agent_receiver.with_client_ip("127.0.0.1"):
        resp = agent_receiver.activate_config(site_cn=site_name)
    assert resp.status_code == HTTPStatus.OK, resp.text

    # Assert each relay has exactly one pending config task with correct serial
    _assert_single_pending_config_task(agent_receiver, serial_folder, relay_id_a)
    _assert_single_pending_config_task(agent_receiver, serial_folder, relay_id_b)


def test_activation_performed_twice_with_new_config(
    site: SiteMock,
    agent_receiver: AgentReceiverClient,
    site_context: Config,
    site_name: str,
) -> None:
    """Verify that performing activation with a new configuration creates new config tasks with the updated serial.

    Test steps:
    1. Configure agent receiver and perform first activation
    2. Create new config and perform second activation
    3. Verify each relay has pending task with new config serial
    """
    # Start AR with two relays configured in the site
    relay_id_a = str(uuid.uuid4())
    relay_id_b = str(uuid.uuid4())
    site.set_scenario([relay_id_a, relay_id_b])

    config_a = create_config_folder(site_context.omd_root, [relay_id_a, relay_id_b])
    agent_receiver.set_serial(config_a.serial)

    # Simulate user activation. Call to the endpoint that creates a ActivateConfigTask for each relay
    with agent_receiver.with_client_ip("127.0.0.1"):
        resp = agent_receiver.activate_config(site_cn=site_name)
    assert resp.status_code == HTTPStatus.OK, resp.text

    # Assert each relay has exactly one pending config task with correct serial
    _assert_single_pending_config_task(agent_receiver, config_a, relay_id_a)
    _assert_single_pending_config_task(agent_receiver, config_a, relay_id_b)

    # Create a new configuration folder simulating a new config activation by user
    config_b = create_config_folder(site_context.omd_root, [relay_id_a, relay_id_b])
    agent_receiver.set_serial(config_b.serial)

    # Simulate second user activation.
    with agent_receiver.with_client_ip("127.0.0.1"):
        resp = agent_receiver.activate_config(site_cn=site_name)
    assert resp.status_code == HTTPStatus.OK, resp.text

    # Assert each relay has the new pending config task with correct serial
    _assert_pending_config_task_is_present(agent_receiver, config_b, relay_id_a)
    _assert_pending_config_task_is_present(agent_receiver, config_b, relay_id_b)


def test_new_relays_when_activation_performed(
    site: SiteMock,
    site_client: httpx.Client,
    agent_receiver: AgentReceiverClient,
    site_context: Config,
    site_name: str,
) -> None:
    """Verify that activation creates config tasks for newly added relays while maintaining tasks for existing relays.

    Test steps:
    1. Configure agent receiver with two relays and activate
    2. Add a third relay and perform second activation
    3. Verify all three relays have pending config tasks
    """
    # Start AR with two relays configured in the site
    relay_id_a = str(uuid.uuid4())
    relay_id_b = str(uuid.uuid4())
    relay_id_c = str(uuid.uuid4())
    site.set_scenario(relays=[relay_id_a, relay_id_b], changes=[(relay_id_c, OP.ADD)])

    config_a = create_config_folder(site_context.omd_root, [relay_id_a, relay_id_b])
    agent_receiver.set_serial(config_a.serial)

    # Simulate user activation. Call to the endpoint that creates a ActivateConfigTask for each relay
    with agent_receiver.with_client_ip("127.0.0.1"):
        resp = agent_receiver.activate_config(site_cn=site_name)
    assert resp.status_code == HTTPStatus.OK, resp.text

    # Assert each relay has exactly one pending config task with correct serial
    _assert_single_pending_config_task(agent_receiver, config_a, relay_id_a)
    _assert_single_pending_config_task(agent_receiver, config_a, relay_id_b)
    tasks = get_relay_tasks(agent_receiver, relay_id_c)
    assert len(tasks.tasks) == 0

    # Add new relay in the site mock
    site_client.post(
        "/domain-types/relay/collections/all",
        json={
            "alias": relay_id_c,
            "siteid": site.site_name,
            "num_fetchers": 17,
            "log_level": "INFO",
        },
    )
    # Create a new configuration folder with new relays in site simulating a new config activation by user
    config_b = create_config_folder(site_context.omd_root, [relay_id_a, relay_id_b, relay_id_c])
    agent_receiver.set_serial(config_b.serial)

    # Simulate second user activation.
    with agent_receiver.with_client_ip("127.0.0.1"):
        resp = agent_receiver.activate_config(site_cn=site_name)
    assert resp.status_code == HTTPStatus.OK, resp.text

    # Assert each relay has the new pending config task with correct serial
    _assert_pending_config_task_is_present(agent_receiver, config_b, relay_id_a)
    _assert_pending_config_task_is_present(agent_receiver, config_b, relay_id_b)
    _assert_pending_config_task_is_present(agent_receiver, config_b, relay_id_c)


def test_removed_relays_when_activation_performed(
    site: SiteMock,
    site_client: httpx.Client,
    agent_receiver: AgentReceiverClient,
    site_context: Config,
    site_name: str,
) -> None:
    """Verify that activation correctly handles scenarios where relays have been removed from the configuration.

    Test steps:
    1. Configure agent receiver with two relays and activate
    2. Remove one relay and perform second activation
    3. Verify remaining relay has pending task and removed relay tasks persist
    """
    # Start AR with two relays configured in the site
    relay_id_a = str(uuid.uuid4())
    relay_id_b = str(uuid.uuid4())
    site.set_scenario(relays=[relay_id_a, relay_id_b], changes=[(relay_id_a, OP.DEL)])

    config_a = create_config_folder(site_context.omd_root, [relay_id_a, relay_id_b])
    agent_receiver.set_serial(config_a.serial)

    # Simulate user activation. Call to the endpoint that creates a ActivateConfigTask for each relay
    with agent_receiver.with_client_ip("127.0.0.1"):
        resp = agent_receiver.activate_config(site_cn=site_name)
    assert resp.status_code == HTTPStatus.OK, resp.text

    # Assert each relay has exactly one pending config task with correct serial
    _assert_single_pending_config_task(agent_receiver, config_a, relay_id_a)
    _assert_single_pending_config_task(agent_receiver, config_a, relay_id_b)

    # Remove relay_a in the site mock
    site_client.delete(f"/objects/relay/{relay_id_a}")
    # Create a new configuration folder with new relays in site simulating a new config activation by user
    config_b = create_config_folder(site_context.omd_root, [relay_id_b])
    agent_receiver.set_serial(config_b.serial)

    # Simulate second user activation.
    with agent_receiver.with_client_ip("127.0.0.1"):
        resp = agent_receiver.activate_config(site_cn=site_name)
    assert resp.status_code == HTTPStatus.OK, resp.text

    # Assert each relay has the new pending config task with correct serial
    _assert_pending_config_task_is_present(agent_receiver, config_b, relay_id_b)

    # Currently tasks for removed relays are not deleted. They remain in the system.
    # This case must be handled eventually if proper logic for removed relays is defined.
    _assert_pending_config_task_is_present(agent_receiver, config_a, relay_id_a)


def test_activation_with_no_relays(
    site: SiteMock,
    agent_receiver: AgentReceiverClient,
    site_context: Config,
    site_name: str,
) -> None:
    """Verify that config activation succeeds gracefully when no relays are configured.

    Test steps:
    1. Configure agent receiver with no relays
    2. Perform config activation
    3. Verify endpoint responds successfully with no tasks created
    """
    # Start AR with no relays configured in the site
    site.set_scenario([])

    cf = create_config_folder(site_context.omd_root, [])
    agent_receiver.set_serial(cf.serial)

    # Simulate user activation with no relays
    with agent_receiver.with_client_ip("127.0.0.1"):
        resp = agent_receiver.activate_config(site_cn=site_name)
    assert resp.status_code == HTTPStatus.OK, resp.text

    # No tasks should be created since there are no relays
    # This test mainly ensures the endpoint doesn't crash with empty relay list


def test_activation_with_mixed_relay_task_states(
    site: SiteMock,
    agent_receiver: AgentReceiverClient,
    site_context: Config,
    site_name: str,
) -> None:
    """Verify that activation creates new pending tasks only for relays whose previous config tasks are finished, not for those with pending tasks.

    Test steps:
    1. Activate config creating pending tasks for two relays
    2. Complete one relay's task, leaving the other pending
    3. Verify second activation creates new task only for completed relay
    """
    # Start AR with two relays configured in the site
    relay_id_a = str(uuid.uuid4())
    relay_id_b = str(uuid.uuid4())
    site.set_scenario([relay_id_a, relay_id_b])

    serial_folder = create_config_folder(site_context.omd_root, [relay_id_a, relay_id_b])
    agent_receiver.set_serial(serial_folder.serial)

    # First activation - creates pending tasks for both relays
    with agent_receiver.with_client_ip("127.0.0.1"):
        resp = agent_receiver.activate_config(site_cn=site_name)
    assert resp.status_code == HTTPStatus.OK, resp.text

    # Verify both relays have pending tasks
    _assert_single_pending_config_task(agent_receiver, serial_folder, relay_id_a)
    _assert_single_pending_config_task(agent_receiver, serial_folder, relay_id_b)

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
    _assert_single_pending_config_task(agent_receiver, serial_folder, relay_id_b)
    tasks = get_relay_tasks(agent_receiver, relay_id_a)
    assert len(tasks.tasks) == 1
    assert tasks.tasks[0].status == TaskStatus.FINISHED

    # Second activation - should create new pending tasks ONLY for relay_id_a since its previous task is finished
    with agent_receiver.with_client_ip("127.0.0.1"):
        resp = agent_receiver.activate_config(site_cn=site_name)
    assert resp.status_code == HTTPStatus.OK, resp.text

    _assert_single_pending_config_task(agent_receiver, serial_folder, relay_id_b)

    tasks_a = get_relay_tasks(agent_receiver, relay_id_a)
    assert len(tasks_a.tasks) == 2
    assert all(
        isinstance(task.spec, RelayConfigTask) and task.spec.serial == serial_folder.serial.value
        for task in tasks_a.tasks
    )
    task_statuses = [task.status for task in tasks_a.tasks]
    assert TaskStatus.PENDING in task_statuses, f"Expected PENDING status in {task_statuses}"
    assert TaskStatus.FINISHED in task_statuses, f"Expected FINISHED status in {task_statuses}"


def test_activation_with_relay_pending_activation_handles_gracefully(
    site: SiteMock,
    agent_receiver: AgentReceiverClient,
    site_context: Config,
    site_name: str,
) -> None:
    """Verify that activation gracefully handles relays pending activation without errors.

    This test ensures that when a relay is registered in the agent receiver but doesn't have
    its configuration applied yet (relay_config_applied returns False), the system:
    1. Handles it as an expected scenario (no errors raised or logged)
    2. Does not create config tasks for the pending relay
    3. Proceeds normally with configured relays
    4. Returns HTTP 200 indicating successful activation

    Test steps:
    1. Register three relays in the agent receiver
    2. Create config folders only for two of them (third is pending activation)
    3. Perform config activation
    4. Verify activation succeeds with HTTP 200
    5. Verify configured relays get tasks
    6. Verify pending relay is skipped (no tasks created)
    """
    # Register three relays in the agent receiver
    relay_id_configured_1 = str(uuid.uuid4())
    relay_id_configured_2 = str(uuid.uuid4())
    relay_id_pending = str(uuid.uuid4())
    site.set_scenario([relay_id_configured_1, relay_id_configured_2, relay_id_pending])

    # Create config folders only for two relays - third relay is pending activation
    # This simulates the scenario where a relay is registered but not yet configured
    serial_folder = create_config_folder(
        site_context.omd_root, [relay_id_configured_1, relay_id_configured_2]
    )
    agent_receiver.set_serial(serial_folder.serial)

    # Perform config activation - this should succeed despite pending relay
    with agent_receiver.with_client_ip("127.0.0.1"):
        resp = agent_receiver.activate_config(site_cn=site_name)

    # Verify activation succeeded
    assert resp.status_code == HTTPStatus.OK, (
        f"Expected HTTP 200 but got {resp.status_code}: {resp.text}. "
        f"Activation should succeed even with relays pending activation."
    )

    # Verify configured relays have tasks created
    _assert_single_pending_config_task(agent_receiver, serial_folder, relay_id_configured_1)
    _assert_single_pending_config_task(agent_receiver, serial_folder, relay_id_configured_2)

    # Verify pending relay has no tasks (correctly skipped as expected behavior)
    tasks_pending = get_relay_tasks(agent_receiver, relay_id_pending)
    assert len(tasks_pending.tasks) == 0, (
        f"Expected no tasks for pending relay {relay_id_pending} (not yet configured), "
        f"but found {len(tasks_pending.tasks)} tasks: {tasks_pending.tasks}"
    )


def _assert_single_pending_config_task(
    agent_receiver: AgentReceiverClient,
    serial_folder: ConfigFolder,
    relay_id: str,
) -> None:
    resp = get_relay_tasks(agent_receiver, relay_id)
    assert len(resp.tasks) == 1, resp

    task = _assert_config_task_exists(
        resp.tasks,
        expected_status=TaskStatus.PENDING,
        expected_serial=serial_folder.serial,
    )
    serial_folder.assert_tar_content(relay_id, task.tar_data)


def _assert_pending_config_task_is_present(
    agent_receiver: AgentReceiverClient,
    serial_folder: ConfigFolder,
    relay_id: str,
) -> None:
    resp = get_relay_tasks(agent_receiver, relay_id)
    task = _assert_config_task_exists(
        resp.tasks,
        expected_status=TaskStatus.PENDING,
        expected_serial=serial_folder.serial,
    )
    serial_folder.assert_tar_content(relay_id, task.tar_data)


def _assert_config_task_exists(
    tasks: list[TaskResponse],
    expected_status: TaskStatus,
    expected_serial: Serial,
) -> RelayConfigTask:
    for task in tasks:
        if (
            isinstance(task.spec, RelayConfigTask)
            and task.status == expected_status
            and task.spec.serial == expected_serial.value
        ):
            return task.spec
    assert False, (
        f"No task found with status {expected_status}, serial {expected_serial} in {tasks}"
    )
