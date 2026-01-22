#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
import uuid

import pytest

from cmk.agent_receiver.lib.config import Config
from cmk.agent_receiver.relay.lib.shared_types import Serial
from cmk.relay_protocols.tasks import (
    RelayConfigTask,
    ResultType,
    TaskResponse,
    TaskStatus,
)
from cmk.testlib.agent_receiver.agent_receiver import AgentReceiverClient
from cmk.testlib.agent_receiver.config_file_system import create_config_folder
from cmk.testlib.agent_receiver.site_mock import SiteMock
from cmk.testlib.agent_receiver.tasks import add_tasks, get_all_tasks, get_relay_tasks

RESPONSE_PAYLOAD = "some response payload"
TASKS_COUNT = 5


@pytest.mark.parametrize(
    "result_type_input,result_type_output,expected_status",
    [
        pytest.param("OK", ResultType.OK, TaskStatus.FINISHED, id="result type success"),
        pytest.param("ERROR", ResultType.ERROR, TaskStatus.FAILED, id="result type failure"),
    ],
)
def test_updating_task_should_change_stored_task_object(
    relay_id: str,
    agent_receiver: AgentReceiverClient,
    result_type_input: str,
    result_type_output: ResultType,
    expected_status: TaskStatus,
    site_context: Config,
    site_name: str,
) -> None:
    """Verify that updating a task with a result modifies the stored task object and sets the correct task status based on the result type.

    Test steps:
    1. Create a task for the relay
    2. Update the task with a result
    3. Verify the stored task contains the result and correct status
    """

    cf = create_config_folder(root=site_context.omd_root, relays=[relay_id])
    agent_receiver.set_serial(cf.serial)

    task_ids = add_tasks(1, agent_receiver, relay_id, site_name)
    task_id = task_ids[0]

    # do the update
    update_response = agent_receiver.update_task(
        relay_id=relay_id,
        task_id=task_id,
        result_type=result_type_input,
        result_payload=RESPONSE_PAYLOAD,
    ).json()

    task_response = TaskResponse.model_validate(update_response)

    # assert the response and assert the stored task

    assert_task(
        task_response,
        task_id=task_id,
        status=expected_status,
        result_type=result_type_output,
        result_payload=RESPONSE_PAYLOAD,
    )

    stored_tasks = get_all_tasks(agent_receiver, relay_id)
    task = find_task_with_id(task_id, stored_tasks)
    assert_task(
        task,
        task_id=task_id,
        status=expected_status,
        result_type=result_type_output,
        result_payload=RESPONSE_PAYLOAD,
    )


@pytest.mark.parametrize("result_type_input", ["OK", "ERROR"])
def test_task_no_longer_pending(
    agent_receiver: AgentReceiverClient,
    relay_id: str,
    result_type_input: str,
    site_context: Config,
    site_name: str,
) -> None:
    """Verify that once a task has been updated with a result, it no longer appears in the list of pending tasks.

    Test steps:
    1. Create tasks and verify one is pending
    2. Update the task with a result
    3. Verify the task no longer appears in pending tasks list
    """

    cf = create_config_folder(root=site_context.omd_root, relays=[relay_id])
    agent_receiver.set_serial(cf.serial)

    task_ids = add_tasks(3, agent_receiver, relay_id, site_name)
    task_id = task_ids[1]

    all_tasks = get_all_tasks(agent_receiver, relay_id)
    task = find_task_with_id(task_id, all_tasks)
    assert_is_pending_task(task, task_id=task_id)

    all_pending_tasks = get_pending_tasks(agent_receiver, relay_id)
    task = find_task_with_id(task_id, all_pending_tasks)
    assert_is_pending_task(task, task_id)

    _ = agent_receiver.update_task(
        relay_id=relay_id,
        task_id=task_id,
        result_type=result_type_input,
        result_payload=RESPONSE_PAYLOAD,
    )
    all_pending_tasks = get_pending_tasks(agent_receiver, relay_id)
    assert_task_not_in_the_list(task_id, all_pending_tasks)


@pytest.mark.parametrize("result_type_input", ["OK", "ERROR"])
def test_timestamps_are_handled(
    agent_receiver: AgentReceiverClient,
    relay_id: str,
    result_type_input: str,
    site_context: Config,
    site_name: str,
) -> None:
    """Verify that updating a task modifies the update_timestamp but preserves the creation_timestamp.

    Test steps:
    1. Create a task and record its timestamps
    2. Update the task after a delay
    3. Verify creation_timestamp unchanged and update_timestamp increased
    """

    cf = create_config_folder(root=site_context.omd_root, relays=[relay_id])
    agent_receiver.set_serial(cf.serial)

    task_ids = add_tasks(1, agent_receiver, relay_id, site_name)
    task_id = task_ids[0]

    all_tasks = get_all_tasks(agent_receiver, relay_id)
    task_when_created = find_task_with_id(task_id, all_tasks)

    # sleep a bit to ensure different update timestamp
    time.sleep(0.05)

    _ = agent_receiver.update_task(
        relay_id=relay_id,
        task_id=task_id,
        result_type=result_type_input,
        result_payload=RESPONSE_PAYLOAD,
    )

    all_tasks = get_all_tasks(agent_receiver, relay_id)
    task = find_task_with_id(task_id, all_tasks)

    assert task.creation_timestamp == task_when_created.creation_timestamp
    assert task.update_timestamp > task_when_created.update_timestamp


@pytest.mark.parametrize("result_type_input", ["OK", "ERROR"])
def test_the_other_tasks_are_not_changed(
    agent_receiver: AgentReceiverClient,
    relay_id: str,
    result_type_input: str,
    site_context: Config,
    site_name: str,
) -> None:
    """Verify that updating one task does not modify any other tasks that belong to the same relay.

    Test steps:
    1. Create multiple tasks for a relay
    2. Update one task with a result
    3. Verify other tasks remain unchanged
    """

    cf = create_config_folder(root=site_context.omd_root, relays=[relay_id])
    agent_receiver.set_serial(cf.serial)

    task_ids = add_tasks(3, agent_receiver, relay_id, site_name)
    task_id = task_ids[1]

    orig_tasks = get_all_tasks(agent_receiver, relay_id)

    _ = agent_receiver.update_task(
        relay_id=relay_id,
        task_id=task_id,
        result_type=result_type_input,
        result_payload=RESPONSE_PAYLOAD,
    )

    current_tasks = get_all_tasks(agent_receiver, relay_id)

    other_task_ids = set(task_ids)
    other_task_ids.remove(task_id)

    for tid in other_task_ids:
        t1 = find_task_with_id(tid, orig_tasks)
        t2 = find_task_with_id(tid, current_tasks)
        assert t1 == t2


def test_finishing_config_task(
    relay_id: str,
    agent_receiver: AgentReceiverClient,
    site_context: Config,
) -> None:
    """
    Verify that RelayConfigTask can be set to FINISHED status.

    Test steps:
    1. Create config for relay
    2. Request pending tasks using an outdated serial to get a RelayConfigTask
    3. Update serial in client and acknowledge the task with result_type "OK"
    4. Assert that there are no pending tasks and the task is now in FINISHED status
    """
    create_config_folder(root=site_context.omd_root, relays=[relay_id])

    agent_receiver.set_serial(Serial.default())
    relay_tasks = get_relay_tasks(agent_receiver, relay_id, status="PENDING").tasks
    assert len(relay_tasks) == 1
    assert isinstance(relay_tasks[0].spec, RelayConfigTask)

    agent_receiver.set_serial(Serial(relay_tasks[0].spec.serial))
    response = agent_receiver.update_task(
        relay_id=relay_id,
        task_id=relay_tasks[0].id,
        result_type="OK",
        result_payload="It's done",
    )
    assert response.status_code < 400, response.text
    assert 0 == len(get_relay_tasks(agent_receiver, relay_id, status="PENDING").tasks)
    finished_tasks = get_relay_tasks(agent_receiver, relay_id, status="FINISHED").tasks
    assert 1 == len(finished_tasks)
    assert relay_tasks[0].id == finished_tasks[0].id


@pytest.fixture
def relay_id(site: SiteMock) -> str:
    relay_id = str(uuid.uuid4())
    site.set_scenario(relay_id)
    return relay_id


def get_pending_tasks(agent_receiver: AgentReceiverClient, relay_id: str) -> list[TaskResponse]:
    return get_relay_tasks(agent_receiver, relay_id, status="PENDING").tasks


def find_task_with_id(task_id: str, tasks: list[TaskResponse]) -> TaskResponse:
    matching_tasks = [t for t in tasks if str(t.id) == task_id]
    assert len(matching_tasks) == 1, f"Found tasks: {matching_tasks}"
    return matching_tasks[0]


def assert_task(
    task: TaskResponse,
    *,
    task_id: str,
    status: TaskStatus,
    result_type: ResultType | None,
    result_payload: str | None,
) -> None:
    assert str(task.id) == task_id
    assert task.status == status
    assert task.result_type == result_type
    assert task.result_payload == result_payload


def assert_is_pending_task(task: TaskResponse, task_id: str) -> None:
    assert_task(
        task, task_id=task_id, status=TaskStatus.PENDING, result_type=None, result_payload=None
    )


def assert_task_not_in_the_list(task_id: str, tasks: list[TaskResponse]) -> None:
    assert not any(str(t.id) == task_id for t in tasks)
