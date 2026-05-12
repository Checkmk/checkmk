#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
import uuid
from http import HTTPStatus

import pytest
from fastapi.testclient import TestClient

from cmk.agent_receiver.relay.lib.shared_types import Serial
from cmk.relay_protocols.tasks import (
    RelayConfigTask,
    ResultType,
    TaskListResponse,
    TaskResponse,
    TaskStatus,
)
from cmk.testlib.agent_receiver.clients import RelayClient, SiteClient
from cmk.testlib.agent_receiver.relay_config_generator import RelayConfig
from cmk.testlib.agent_receiver.site_mock import SiteMock

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
    test_client: TestClient,
    result_type_input: str,
    result_type_output: ResultType,
    expected_status: TaskStatus,
    site: SiteMock,
) -> None:
    """Verify that updating a task with a result modifies the stored task object and sets the correct task status based on the result type.

    Test steps:
    1. Create a task for the relay
    2. Update the task with a result
    3. Verify the stored task contains the result and correct status
    """
    relay = RelayClient(test_client, site.site_name, relay_id)
    relay.apply_config(site.push_config([relay_id]))

    site_c = SiteClient(test_client, site.site_name)
    task_ids = site_c.add_tasks(1, relay_id)
    task_id = task_ids[0]

    # do the update
    update_response = relay.update_task(
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

    stored_tasks = relay.get_task_list().tasks
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
    test_client: TestClient,
    relay_id: str,
    result_type_input: str,
    site: SiteMock,
) -> None:
    """Verify that once a task has been updated with a result, it no longer appears in the list of pending tasks.

    Test steps:
    1. Create tasks and verify one is pending
    2. Update the task with a result
    3. Verify the task no longer appears in pending tasks list
    """
    relay = RelayClient(test_client, site.site_name, relay_id)
    relay.apply_config(site.push_config([relay_id]))

    site_c = SiteClient(test_client, site.site_name)
    task_ids = site_c.add_tasks(3, relay_id)
    task_id = task_ids[1]

    all_tasks = relay.get_task_list().tasks
    task = find_task_with_id(task_id, all_tasks)
    assert_is_pending_task(task, task_id=task_id)

    all_pending_tasks = relay.get_task_list(status="PENDING").tasks
    task = find_task_with_id(task_id, all_pending_tasks)
    assert_is_pending_task(task, task_id)

    _ = relay.update_task(
        task_id=task_id,
        result_type=result_type_input,
        result_payload=RESPONSE_PAYLOAD,
    )
    all_pending_tasks = relay.get_task_list(status="PENDING").tasks
    assert_task_not_in_the_list(task_id, all_pending_tasks)


@pytest.mark.parametrize("result_type_input", ["OK", "ERROR"])
def test_timestamps_are_handled(
    test_client: TestClient,
    relay_id: str,
    result_type_input: str,
    site: SiteMock,
) -> None:
    """Verify that updating a task modifies the update_timestamp but preserves the creation_timestamp.

    Test steps:
    1. Create a task and record its timestamps
    2. Update the task after a delay
    3. Verify creation_timestamp unchanged and update_timestamp increased
    """
    relay = RelayClient(test_client, site.site_name, relay_id)
    relay.apply_config(site.push_config([relay_id]))

    site_c = SiteClient(test_client, site.site_name)
    task_ids = site_c.add_tasks(1, relay_id)
    task_id = task_ids[0]

    all_tasks = relay.get_task_list().tasks
    task_when_created = find_task_with_id(task_id, all_tasks)

    # sleep a bit to ensure different update timestamp
    time.sleep(0.05)

    _ = relay.update_task(
        task_id=task_id,
        result_type=result_type_input,
        result_payload=RESPONSE_PAYLOAD,
    )

    all_tasks = relay.get_task_list().tasks
    task = find_task_with_id(task_id, all_tasks)

    assert task.creation_timestamp == task_when_created.creation_timestamp
    assert task.update_timestamp > task_when_created.update_timestamp


@pytest.mark.parametrize("result_type_input", ["OK", "ERROR"])
def test_the_other_tasks_are_not_changed(
    test_client: TestClient,
    relay_id: str,
    result_type_input: str,
    site: SiteMock,
) -> None:
    """Verify that updating one task does not modify any other tasks that belong to the same relay.

    Test steps:
    1. Create multiple tasks for a relay
    2. Update one task with a result
    3. Verify other tasks remain unchanged
    """
    relay = RelayClient(test_client, site.site_name, relay_id)
    relay.apply_config(site.push_config([relay_id]))

    site_c = SiteClient(test_client, site.site_name)
    task_ids = site_c.add_tasks(3, relay_id)
    task_id = task_ids[1]

    orig_tasks = relay.get_task_list().tasks

    _ = relay.update_task(
        task_id=task_id,
        result_type=result_type_input,
        result_payload=RESPONSE_PAYLOAD,
    )

    current_tasks = relay.get_task_list().tasks

    other_task_ids = set(task_ids)
    other_task_ids.remove(task_id)

    for tid in other_task_ids:
        t1 = find_task_with_id(tid, orig_tasks)
        t2 = find_task_with_id(tid, current_tasks)
        assert t1 == t2


def test_finishing_config_task(
    test_client: TestClient,
    relay_id: str,
    site: SiteMock,
) -> None:
    """
    Verify that RelayConfigTask can be set to FINISHED status.

    Test steps:
    1. Create config for relay
    2. Request pending tasks using an outdated serial to get a RelayConfigTask
    3. Update serial in client and acknowledge the task with result_type "OK"
    4. Assert that there are no pending tasks and the task is now in FINISHED status
    """
    pushed_config = site.push_config([relay_id])

    relay = RelayClient(test_client, site.site_name, relay_id)
    # Start with outdated serial to trigger config task
    relay.apply_config(RelayConfig(serial=Serial.default(), files={}))
    relay_tasks_resp = relay.get_tasks(status="PENDING")
    assert relay_tasks_resp.status_code == HTTPStatus.OK, relay_tasks_resp.text
    relay_tasks = TaskListResponse.model_validate(relay_tasks_resp.json()).tasks
    assert len(relay_tasks) == 1
    assert isinstance(relay_tasks[0].spec, RelayConfigTask)

    # Apply the config with the serial from the config task
    relay.apply_config(
        RelayConfig(serial=Serial(relay_tasks[0].spec.serial), files=pushed_config.files)
    )
    response = relay.update_task(
        task_id=relay_tasks[0].id,
        result_type="OK",
        result_payload="It's done",
    )
    assert response.status_code < 400, response.text
    assert 0 == len(relay.get_task_list(status="PENDING").tasks)
    finished_tasks = relay.get_task_list(status="FINISHED").tasks
    assert 1 == len(finished_tasks)
    assert relay_tasks[0].id == finished_tasks[0].id


@pytest.fixture
def relay_id(site: SiteMock) -> str:
    relay_id = str(uuid.uuid4())
    site.set_scenario(relay_id)
    return relay_id


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
