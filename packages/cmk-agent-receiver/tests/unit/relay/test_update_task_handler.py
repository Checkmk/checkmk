#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.agent_receiver.relay.api.routers.tasks.handlers.update_task import (
    UpdateTaskHandler,
)
from cmk.agent_receiver.relay.api.routers.tasks.libs.tasks_repository import (
    RelayTask,
    ResultType,
    TasksRepository,
)
from cmk.agent_receiver.relay.lib.relays_repository import RelaysRepository
from cmk.agent_receiver.relay.lib.shared_types import (
    RelayID,
    RelayNotFoundError,
    TaskID,
    TaskNotFoundError,
)
from cmk.agent_receiver.relay.lib.site_auth import UserAuth


@pytest.mark.usefixtures("site_context")
def test_process_update_task(
    update_task_handler: UpdateTaskHandler,
    populated_repos: tuple[RelayID, RelayTask, RelaysRepository, TasksRepository],
) -> None:
    relay_id, task, relays_repository, tasks_repository = populated_repos

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
    assert isinstance(tasks_enqueued[0], type(task))
    assert tasks_enqueued[0].spec == task.spec
    # TODO: assert tasks_enqueued[0].status == TaskStatus.FINISHED or TaskStatus.ERROR
    assert tasks_enqueued[0].result_type == ResultType.OK
    assert tasks_enqueued[0].result_payload == "Task completed successfully"


@pytest.mark.usefixtures("site_context")
def test_process_update_task_non_existent_relay(update_task_handler: UpdateTaskHandler) -> None:
    # arrange
    relay_id = RelayID("non-existent-relay-id")

    # act
    with pytest.raises(RelayNotFoundError):
        update_task_handler.process(
            relay_id=relay_id,
            task_id=TaskID("any-task-id"),
            result_type=ResultType.OK,
            result_payload="any payload",
        )


@pytest.mark.usefixtures("site_context")
def test_process_update_task_non_existent_task(
    relays_repository: RelaysRepository,
    update_task_handler: UpdateTaskHandler,
    test_user: UserAuth,
) -> None:
    # arrange
    # register a relay in the repository
    relay_id = relays_repository.add_relay(test_user, alias="test-relay")

    task_id = TaskID("non-existent-task-id")

    # act
    with pytest.raises(TaskNotFoundError):
        update_task_handler.process(
            relay_id=relay_id,
            task_id=task_id,
            result_type=ResultType.OK,
            result_payload="any payload",
        )
