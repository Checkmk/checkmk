#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: Checkmk Enterprise License
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time

import pytest

from cmk.agent_receiver.relay.api.routers.tasks.libs.tasks_repository import TaskID
from cmk.relay_protocols.tasks import (
    ResultType,
    TaskResponse,
    TaskStatus,
    TaskType,
)

from .test_lib.agent_receiver import AgentReceiverClient, register_relay
from .test_lib.tasks import get_relay_tasks, push_task

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
) -> None:
    """
    The stored task object should be modified so that it contains the result.
    The task status should reflect the type of the attached result.
    """
    task_ids = add_tasks(1, agent_receiver, relay_id)
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
    agent_receiver: AgentReceiverClient, relay_id: str, result_type_input: str
) -> None:
    """
    Once a task has been updated with a result, it should no longer appear in the list of pending tasks.
    """

    task_ids = add_tasks(3, agent_receiver, relay_id)
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
    agent_receiver: AgentReceiverClient, relay_id: str, result_type_input: str
) -> None:
    """
    A call to update task should modify the "update_timestamp" values and it should not
    modify the "creation_timestamp" value.
    """

    task_ids = add_tasks(1, agent_receiver, relay_id)
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
) -> None:
    """
    A call to update task should not modify any other possible tasks that belong to the relay.
    """

    task_ids = add_tasks(3, agent_receiver, relay_id)
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


@pytest.fixture
def relay_id(agent_receiver: AgentReceiverClient) -> str:
    return register_relay(agent_receiver)


def add_tasks(count: int, agent_receiver: AgentReceiverClient, relay_id: str) -> list[TaskID]:
    gen = (
        push_task(
            agent_receiver=agent_receiver,
            relay_id=relay_id,
            task_type=TaskType.FETCH_AD_HOC,
            task_payload=f"payload_{i}",
        )
        for i in range(count)
    )
    result = [TaskID(str(r.task_id)) for r in gen if r is not None]
    assert len(result) == count
    return result


def get_all_tasks(agent_receiver: AgentReceiverClient, relay_id: str) -> list[TaskResponse]:
    return get_relay_tasks(agent_receiver, relay_id).tasks


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
