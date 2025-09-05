#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest
from pydantic import SecretStr

from cmk.agent_receiver.relay.api.routers.tasks.handlers.get_tasks import (
    GetRelayTaskHandler,
    GetRelayTasksHandler,
    RelayNotFoundError,
)
from cmk.agent_receiver.relay.api.routers.tasks.libs.tasks_repository import (
    Task,
    TaskNotFoundError,
    TasksRepository,
    TaskStatus,
)
from cmk.agent_receiver.relay.lib.relays_repository import RelaysRepository
from cmk.agent_receiver.relay.lib.shared_types import RelayID, TaskID


def test_get_task_handler(
    get_task_handler: GetRelayTaskHandler,
    populated_repos: tuple[RelayID, Task, RelaysRepository, TasksRepository],
    test_authorization: SecretStr,
) -> None:
    relay_id, task, relays_repository, tasks_repository = populated_repos

    handled_task = get_task_handler.process(
        relay_id=relay_id, task_id=task.id, authorization=test_authorization
    )
    assert handled_task == task


def test_get_task_handler_with_unknown_relay(
    get_task_handler: GetRelayTaskHandler,
    populated_repos: tuple[RelayID, Task, RelaysRepository, TasksRepository],
    test_authorization: SecretStr,
) -> None:
    relay_id, task, relays_repository, tasks_repository = populated_repos

    with pytest.raises(RelayNotFoundError):
        get_task_handler.process(
            relay_id=RelayID("unknown-relay-id"), task_id=task.id, authorization=test_authorization
        )


def test_get_task_handler_with_unknown_task(
    get_task_handler: GetRelayTaskHandler,
    populated_repos: tuple[RelayID, Task, RelaysRepository, TasksRepository],
    test_authorization: SecretStr,
) -> None:
    relay_id, task, relays_repository, tasks_repository = populated_repos

    with pytest.raises(TaskNotFoundError):
        get_task_handler.process(
            relay_id=relay_id, task_id=TaskID("unknown-task-id"), authorization=test_authorization
        )


def test_get_tasks_handler(
    get_tasks_handler: GetRelayTasksHandler,
    populated_repos: tuple[RelayID, Task, RelaysRepository, TasksRepository],
    test_authorization: SecretStr,
) -> None:
    relay_id, task, relays_repository, tasks_repository = populated_repos

    handled_tasks = get_tasks_handler.process(
        relay_id=relay_id, status=None, authorization=test_authorization
    )
    assert handled_tasks == [task]


def test_get_tasks_handler_with_filter(
    get_tasks_handler: GetRelayTasksHandler,
    populated_repos: tuple[RelayID, Task, RelaysRepository, TasksRepository],
    test_authorization: SecretStr,
) -> None:
    relay_id, task, relays_repository, tasks_repository = populated_repos
    handled_tasks = get_tasks_handler.process(
        relay_id=relay_id, status=TaskStatus.FINISHED, authorization=test_authorization
    )
    assert handled_tasks == []


def test_get_task_handler_raises_error_if_relay_is_unknown(
    get_tasks_handler: GetRelayTasksHandler,
    populated_repos: tuple[RelayID, Task, RelaysRepository, TasksRepository],  # noqa: ARG001
    test_authorization: SecretStr,
) -> None:
    with pytest.raises(RelayNotFoundError):
        get_tasks_handler.process(
            relay_id=RelayID("unknown-relay-id"), status=None, authorization=test_authorization
        )
