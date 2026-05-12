#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import uuid
from http import HTTPStatus

from fastapi.testclient import TestClient

from cmk.agent_receiver.relay.lib.shared_types import Serial
from cmk.relay_protocols.tasks import RelayConfigTask, TaskResponse, TaskStatus
from cmk.testlib.agent_receiver.clients import RelayClient, SiteClient
from cmk.testlib.agent_receiver.relay_config_generator import assert_config_tar, RelayConfig
from cmk.testlib.agent_receiver.site_mock import (
    OP,
    SiteMock,
)


def test_activation_performed_by_user_creates_config_tasks_for_each_relay(
    test_client: TestClient,
    site: SiteMock,
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

    serial_folder = site.push_config([relay_id_a, relay_id_b])
    relay_a = RelayClient(test_client, site.site_name, relay_id_a)
    relay_a.apply_config(serial_folder)
    relay_b = RelayClient(test_client, site.site_name, relay_id_b)
    relay_b.apply_config(serial_folder)

    # Simulate user activation. Call to the endpoint that creates a ActivateConfigTask for each relay
    site_ar = SiteClient(test_client, site.site_name)
    resp = site_ar.activate_config()
    assert resp.status_code == HTTPStatus.OK, resp.text

    # Assert each relay has exactly one pending config task with correct serial
    _assert_single_pending_config_task(relay_a, serial_folder)
    _assert_single_pending_config_task(relay_b, serial_folder)


def test_activation_performed_twice_with_same_config(
    test_client: TestClient,
    site: SiteMock,
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

    serial_folder = site.push_config([relay_id_a, relay_id_b])
    relay_a = RelayClient(test_client, site.site_name, relay_id_a)
    relay_a.apply_config(serial_folder)
    relay_b = RelayClient(test_client, site.site_name, relay_id_b)
    relay_b.apply_config(serial_folder)

    # Simulate user activation. Call to the endpoint that creates a ActivateConfigTask for each relay
    site_ar = SiteClient(test_client, site.site_name)
    resp = site_ar.activate_config()
    assert resp.status_code == HTTPStatus.OK, resp.text

    # Assert each relay has exactly one pending config task with correct serial
    _assert_single_pending_config_task(relay_a, serial_folder)
    _assert_single_pending_config_task(relay_b, serial_folder)

    # Simulate second user activation.
    resp = site_ar.activate_config()
    assert resp.status_code == HTTPStatus.OK, resp.text

    # Assert each relay has exactly one pending config task with correct serial
    _assert_single_pending_config_task(relay_a, serial_folder)
    _assert_single_pending_config_task(relay_b, serial_folder)


def test_activation_performed_twice_with_new_config(
    test_client: TestClient,
    site: SiteMock,
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

    config_a = site.push_config([relay_id_a, relay_id_b])
    relay_a = RelayClient(test_client, site.site_name, relay_id_a)
    relay_a.apply_config(config_a)
    relay_b = RelayClient(test_client, site.site_name, relay_id_b)
    relay_b.apply_config(config_a)

    # Simulate user activation. Call to the endpoint that creates a ActivateConfigTask for each relay
    site_ar = SiteClient(test_client, site.site_name)
    resp = site_ar.activate_config()
    assert resp.status_code == HTTPStatus.OK, resp.text

    # Assert each relay has exactly one pending config task with correct serial
    _assert_single_pending_config_task(relay_a, config_a)
    _assert_single_pending_config_task(relay_b, config_a)

    # Create a new configuration folder simulating a new config activation by user
    config_b = site.push_config([relay_id_a, relay_id_b])
    relay_a.apply_config(config_b)
    relay_b.apply_config(config_b)

    # Simulate second user activation.
    resp = site_ar.activate_config()
    assert resp.status_code == HTTPStatus.OK, resp.text

    # Assert each relay has the new pending config task with correct serial
    _assert_pending_config_task_is_present(relay_a, config_b)
    _assert_pending_config_task_is_present(relay_b, config_b)


def test_new_relays_when_activation_performed(
    test_client: TestClient,
    site: SiteMock,
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

    config_a = site.push_config([relay_id_a, relay_id_b])
    relay_a = RelayClient(test_client, site.site_name, relay_id_a)
    relay_a.apply_config(config_a)
    relay_b = RelayClient(test_client, site.site_name, relay_id_b)
    relay_b.apply_config(config_a)

    # Simulate user activation. Call to the endpoint that creates a ActivateConfigTask for each relay
    site_ar = SiteClient(test_client, site.site_name)
    resp = site_ar.activate_config()
    assert resp.status_code == HTTPStatus.OK, resp.text

    # Assert each relay has exactly one pending config task with correct serial
    _assert_single_pending_config_task(relay_a, config_a)
    _assert_single_pending_config_task(relay_b, config_a)
    tasks = RelayClient(test_client, site.site_name, relay_id_c).get_task_list()
    assert len(tasks.tasks) == 0

    # Add new relay in the site mock
    site.add_relay(relay_id_c)
    # Create a new configuration folder with new relays in site simulating a new config activation by user
    config_b = site.push_config([relay_id_a, relay_id_b, relay_id_c])
    relay_a.apply_config(config_b)
    relay_b.apply_config(config_b)
    relay_c = RelayClient(test_client, site.site_name, relay_id_c)
    relay_c.apply_config(config_b)

    # Simulate second user activation.
    resp = site_ar.activate_config()
    assert resp.status_code == HTTPStatus.OK, resp.text

    # Assert each relay has the new pending config task with correct serial
    _assert_pending_config_task_is_present(relay_a, config_b)
    _assert_pending_config_task_is_present(relay_b, config_b)
    _assert_pending_config_task_is_present(relay_c, config_b)


def test_removed_relays_when_activation_performed(
    test_client: TestClient,
    site: SiteMock,
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

    config_a = site.push_config([relay_id_a, relay_id_b])
    relay_a = RelayClient(test_client, site.site_name, relay_id_a)
    relay_a.apply_config(config_a)
    relay_b = RelayClient(test_client, site.site_name, relay_id_b)
    relay_b.apply_config(config_a)

    # Simulate user activation. Call to the endpoint that creates a ActivateConfigTask for each relay
    site_ar = SiteClient(test_client, site.site_name)
    resp = site_ar.activate_config()
    assert resp.status_code == HTTPStatus.OK, resp.text

    # Assert each relay has exactly one pending config task with correct serial
    _assert_single_pending_config_task(relay_a, config_a)
    _assert_single_pending_config_task(relay_b, config_a)

    # Remove relay_a in the site mock
    site.delete_relay(relay_id_a)
    # Create a new configuration folder with new relays in site simulating a new config activation by user
    config_b = site.push_config([relay_id_b])
    relay_b.apply_config(config_b)

    # Simulate second user activation.
    resp = site_ar.activate_config()
    assert resp.status_code == HTTPStatus.OK, resp.text

    # Assert each relay has the new pending config task with correct serial
    _assert_pending_config_task_is_present(relay_b, config_b)

    # Currently tasks for removed relays are not deleted. They remain in the system.
    # This case must be handled eventually if proper logic for removed relays is defined.
    _assert_pending_config_task_is_present(relay_a, config_a)


def test_activation_with_no_relays(
    test_client: TestClient,
    site: SiteMock,
) -> None:
    """Verify that config activation succeeds gracefully when no relays are configured.

    Test steps:
    1. Configure agent receiver with no relays
    2. Perform config activation
    3. Verify endpoint responds successfully with no tasks created
    """
    # Start AR with no relays configured in the site
    site.set_scenario([])

    # No relays to apply config to, but we still push the config
    site.push_config([])

    # Simulate user activation with no relays
    site_ar = SiteClient(test_client, site.site_name)
    resp = site_ar.activate_config()
    assert resp.status_code == HTTPStatus.OK, resp.text

    # No tasks should be created since there are no relays
    # This test mainly ensures the endpoint doesn't crash with empty relay list


def test_activation_with_mixed_relay_task_states(
    test_client: TestClient,
    site: SiteMock,
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

    serial_folder = site.push_config([relay_id_a, relay_id_b])
    relay_a = RelayClient(test_client, site.site_name, relay_id_a)
    relay_a.apply_config(serial_folder)
    relay_b = RelayClient(test_client, site.site_name, relay_id_b)
    relay_b.apply_config(serial_folder)

    # First activation - creates pending tasks for both relays
    site_ar = SiteClient(test_client, site.site_name)
    resp = site_ar.activate_config()
    assert resp.status_code == HTTPStatus.OK, resp.text

    # Verify both relays have pending tasks
    _assert_single_pending_config_task(relay_a, serial_folder)
    _assert_single_pending_config_task(relay_b, serial_folder)

    # Simulate that relay_a's task completed (this would normally happen via relay processing)
    # For this test, we'll assume the task status changed externally
    # The key test is that activation should still work and not create duplicates
    tasks_a = relay_a.get_task_list()
    _ = relay_a.update_task(
        task_id=tasks_a.tasks[0].id,
        result_type="OK",
        result_payload="Config update successful message",
    )
    _assert_single_pending_config_task(relay_b, serial_folder)
    tasks = relay_a.get_task_list()
    assert len(tasks.tasks) == 1
    assert tasks.tasks[0].status == TaskStatus.FINISHED

    # Second activation - should create new pending tasks ONLY for relay_id_a since its previous task is finished
    resp = site_ar.activate_config()
    assert resp.status_code == HTTPStatus.OK, resp.text

    _assert_single_pending_config_task(relay_b, serial_folder)

    tasks_a = relay_a.get_task_list()
    assert len(tasks_a.tasks) == 2
    assert all(
        isinstance(task.spec, RelayConfigTask) and task.spec.serial == serial_folder.serial.value
        for task in tasks_a.tasks
    )
    task_statuses = [task.status for task in tasks_a.tasks]
    assert TaskStatus.PENDING in task_statuses, f"Expected PENDING status in {task_statuses}"
    assert TaskStatus.FINISHED in task_statuses, f"Expected FINISHED status in {task_statuses}"


def test_activation_with_relay_pending_activation_handles_gracefully(
    test_client: TestClient,
    site: SiteMock,
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
    serial_folder = site.push_config([relay_id_configured_1, relay_id_configured_2])
    relay_1 = RelayClient(test_client, site.site_name, relay_id_configured_1)
    relay_1.apply_config(serial_folder)
    relay_2 = RelayClient(test_client, site.site_name, relay_id_configured_2)
    relay_2.apply_config(serial_folder)

    # Perform config activation - this should succeed despite pending relay
    site_ar = SiteClient(test_client, site.site_name)
    resp = site_ar.activate_config()

    # Verify activation succeeded
    assert resp.status_code == HTTPStatus.OK, (
        f"Expected HTTP 200 but got {resp.status_code}: {resp.text}. "
        f"Activation should succeed even with relays pending activation."
    )

    # Verify configured relays have tasks created
    _assert_single_pending_config_task(relay_1, serial_folder)
    _assert_single_pending_config_task(relay_2, serial_folder)

    # Verify pending relay has no tasks (correctly skipped as expected behavior)
    relay_pending = RelayClient(test_client, site.site_name, relay_id_pending)
    tasks_pending = relay_pending.get_task_list()
    assert len(tasks_pending.tasks) == 0, (
        f"Expected no tasks for pending relay {relay_id_pending} (not yet configured), "
        f"but found {len(tasks_pending.tasks)} tasks: {tasks_pending.tasks}"
    )


def _assert_single_pending_config_task(
    relay: RelayClient,
    serial_folder: RelayConfig,
) -> None:
    resp = relay.get_task_list()
    assert len(resp.tasks) == 1, resp

    task = _assert_config_task_exists(
        resp.tasks,
        expected_status=TaskStatus.PENDING,
        expected_serial=serial_folder.serial,
    )
    assert_config_tar(serial_folder, relay.relay_id, task.tar_data)


def _assert_pending_config_task_is_present(
    relay: RelayClient,
    serial_folder: RelayConfig,
) -> None:
    resp = relay.get_task_list()
    task = _assert_config_task_exists(
        resp.tasks,
        expected_status=TaskStatus.PENDING,
        expected_serial=serial_folder.serial,
    )
    assert_config_tar(serial_folder, relay.relay_id, task.tar_data)


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
