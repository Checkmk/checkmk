#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import uuid
from http import HTTPStatus

from fastapi.testclient import TestClient

from cmk.relay_protocols.tasks import RelayConfigTask, TaskListResponse, TaskStatus
from cmk.testlib.agent_receiver.clients import RelayClient
from cmk.testlib.agent_receiver.relay_config_generator import assert_config_tar
from cmk.testlib.agent_receiver.site_mock import SiteMock


def test_config_update_triggered_by_outdated_serial(
    site: SiteMock,
    test_client: TestClient,
) -> None:
    """Verify that requesting tasks with an outdated serial automatically triggers creation of a config update task with the current serial.

    Test steps:
    1. Register two relays with current config
    2. Request tasks with outdated serial
    3. Verify config task is created with correct serial
    """
    relay_id_1 = str(uuid.uuid4())
    relay_id_2 = str(uuid.uuid4())
    site.set_scenario([relay_id_1, relay_id_2])
    old_config = site.push_config([relay_id_1, relay_id_2])

    relay_1 = RelayClient(test_client, site.site_name, relay_id_1)
    relay_1.apply_config(old_config)
    new_config = site.push_config([relay_id_1, relay_id_2])

    relay_1_tasks = _get_relay_tasks(relay_1, status="PENDING").tasks

    assert len(relay_1_tasks) == 1
    task = relay_1_tasks[0]
    assert isinstance(task.spec, RelayConfigTask)
    assert task.spec.serial == new_config.serial.value
    assert_config_tar(new_config, relay_id_1, task.spec.tar_data)

    # relay applies the new config — no update task created
    relay_1.apply_config(new_config)
    relay_2 = RelayClient(test_client, site.site_name, relay_id_2)
    relay_2_tasks = _get_relay_tasks(relay_2, status="PENDING").tasks
    assert len(relay_2_tasks) == 0


def test_config_update_triggered_by_outdated_serial_is_generated_once(
    site: SiteMock,
    test_client: TestClient,
) -> None:
    """Verify that a config update task is created only once when an outdated serial is detected, not on every request.

    Test steps:
    1. Register relay and request tasks with outdated serial
    2. Verify config task is created
    3. Request tasks again and verify same task is returned
    """
    relay_id_1 = str(uuid.uuid4())
    site.set_scenario([relay_id_1])
    old_config = site.push_config([relay_id_1])

    relay_1 = RelayClient(test_client, site.site_name, relay_id_1)
    relay_1.apply_config(old_config)
    new_config = site.push_config([relay_id_1])

    relay_1_tasks = _get_relay_tasks(relay_1, status="PENDING").tasks

    assert len(relay_1_tasks) == 1
    task = relay_1_tasks[0]
    assert isinstance(task.spec, RelayConfigTask)
    assert task.spec.serial == new_config.serial.value
    assert_config_tar(new_config, relay_id_1, task.spec.tar_data)

    tasklist = _get_relay_tasks(relay_1, status="PENDING").tasks
    assert len(tasklist) == 1
    assert tasklist[0].id == task.id


def test_config_update_triggered_by_old_serial_twice_in_a_row(
    site: SiteMock,
    test_client: TestClient,
) -> None:
    """Verify that when the configuration changes, requesting with an outdated serial creates a new config task with the updated serial.

    Test steps:
    1. Create initial config and trigger task with outdated serial
    2. Create new config with different serial
    3. Request tasks with outdated serial again
    4. Verify both config tasks exist with different serials
    """
    relay_id_1 = str(uuid.uuid4())
    site.set_scenario([relay_id_1])

    config_a = site.push_config([relay_id_1])
    relay_1 = RelayClient(test_client, site.site_name, relay_id_1)
    relay_1.apply_config(config_a)
    config_b = site.push_config([relay_id_1])

    tasks_a_first = _get_relay_tasks(relay_1, status="PENDING").tasks

    assert len(tasks_a_first) == 1, (
        f"Expected exactly one task for relay {relay_id_1}, got: {tasks_a_first}"
    )
    first_task = tasks_a_first[0]
    assert isinstance(first_task.spec, RelayConfigTask)
    assert first_task.status == TaskStatus.PENDING
    assert first_task.spec.serial == config_b.serial.value
    assert_config_tar(config_b, relay_id_1, first_task.spec.tar_data)

    relay_1.apply_config(config_b)
    config_c = site.push_config([relay_id_1])

    tasks_a_after = _get_relay_tasks(relay_1, status="PENDING").tasks

    assert len(tasks_a_after) == 2, (
        f"Expected exactly two tasks for relay {relay_id_1}, got: {tasks_a_after}"
    )
    new_task_config = tasks_a_after[1]
    assert isinstance(new_task_config.spec, RelayConfigTask)
    assert new_task_config.status == TaskStatus.PENDING
    assert new_task_config.spec.serial == config_c.serial.value
    assert_config_tar(config_c, relay_id_1, new_task_config.spec.tar_data)


def _get_relay_tasks(relay: RelayClient, status: str | None = None) -> TaskListResponse:
    """Get relay tasks using the relay client."""
    response = relay.get_tasks(status=status)
    assert response.status_code == HTTPStatus.OK, response.text
    return TaskListResponse.model_validate(response.json())
