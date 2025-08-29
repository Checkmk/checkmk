#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import uuid
from collections.abc import Iterator
from datetime import datetime

import pytest

from cmk.agent_receiver.relay.api.routers.tasks.handlers.update_task import (
    RelayNotFoundError,
    TaskNotFoundError,
    UpdateTaskHandler,
)
from cmk.agent_receiver.relay.api.routers.tasks.libs.tasks_repository import (
    ResultType,
    Task,
    TaskID,
    TasksRepository,
    TaskType,
)
from cmk.agent_receiver.relay.lib.relays_repository import (
    RelaysRepository,
)
from cmk.agent_receiver.relay.lib.shared_types import RelayID


@pytest.fixture()
def tasks_repository() -> Iterator[TasksRepository]:
    repository = TasksRepository()
    yield repository


@pytest.fixture()
def relays_repository() -> Iterator[RelaysRepository]:
    repository = RelaysRepository()
    yield repository


@pytest.fixture()
def update_task_handler(
    tasks_repository: TasksRepository, relays_repository: RelaysRepository
) -> Iterator[UpdateTaskHandler]:
    handler = UpdateTaskHandler(
        tasks_repository=tasks_repository, relays_repository=relays_repository
    )
    yield handler


def test_process_update_task(
    update_task_handler: UpdateTaskHandler,
    relays_repository: RelaysRepository,
    tasks_repository: TasksRepository,
) -> None:
    # arrange

    # register a relay in the reposutory
    relay_id = RelayID(str(uuid.uuid4()))
    relays_repository.add_relay(relay_id)

    # insert a task in the repository
    task = Task(
        id=TaskID(str(uuid.uuid4())),
        type=TaskType.FETCH_AD_HOC,
        payload='{"url": "http://example.com/data"}',
        creation_timestamp=datetime.now(),
    )
    tasks_repository.store_task(relay_id=relay_id, task=task)

    # act
    update_task_handler.process(
        relay_id=relay_id,
        task_id=task.id,
        result_type=ResultType.OK,
        result_payload="Task completed successfully",
    )

    # assert
    tasks_enqueued = tasks_repository.get_tasks(relay_id)
    assert len(tasks_enqueued) == 1
    assert tasks_enqueued[0].id == task.id
    assert tasks_enqueued[0].type == task.type
    assert tasks_enqueued[0].payload == task.payload
    # TODO: assert tasks_enqueued[0].status == TaskStatus.FINISHED or TaskStatus.ERROR
    assert tasks_enqueued[0].result_type == ResultType.OK
    assert tasks_enqueued[0].result_payload == "Task completed successfully"


def test_process_create_task_non_existent_relay(update_task_handler: UpdateTaskHandler) -> None:
    # arrange
    relay_id = RelayID(str(uuid.uuid4()))  # Any, non existent

    # act
    with pytest.raises(RelayNotFoundError):
        update_task_handler.process(
            relay_id=relay_id,
            task_id=TaskID(str(uuid.uuid4())),
            result_type=ResultType.OK,
            result_payload="any payload",
        )


def test_process_create_task_non_existent_task(
    relays_repository: RelaysRepository,
    update_task_handler: UpdateTaskHandler,
) -> None:
    # arrange
    # register a relay in the reposutory
    relay_id = RelayID(str(uuid.uuid4()))
    relays_repository.add_relay(relay_id)

    task_id = TaskID(str(uuid.uuid4()))  # Any, non existent

    # act
    with pytest.raises(TaskNotFoundError):
        update_task_handler.process(
            relay_id=relay_id,
            task_id=task_id,
            result_type=ResultType.OK,
            result_payload="any payload",
        )
