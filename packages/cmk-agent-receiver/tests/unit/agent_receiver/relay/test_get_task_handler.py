#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from pathlib import Path

import pytest

from cmk.agent_receiver.config import Config
from cmk.agent_receiver.relay.api.routers.tasks.handlers.get_tasks import (
    GetRelayTaskHandler,
    GetRelayTasksHandler,
)
from cmk.agent_receiver.relay.api.routers.tasks.libs.tasks_repository import (
    RelayTask,
    TasksRepository,
    TaskStatus,
)
from cmk.agent_receiver.relay.lib.relays_repository import RelaysRepository
from cmk.agent_receiver.relay.lib.shared_types import (
    RelayID,
    Serial,
    TaskID,
    TaskNotFoundError,
)
from cmk.testlib.agent_receiver.config_file_system import create_config_folder

SERIAL = Serial("")


@pytest.fixture
def omd_root(site_context: Config) -> Path:
    return site_context.omd_root


def test_get_task_handler(
    get_task_handler: GetRelayTaskHandler,
    populated_repos: tuple[RelayID, RelayTask, RelaysRepository, TasksRepository],
    omd_root: Path,
) -> None:
    relay_id, task, relays_repository, tasks_repository = populated_repos
    _ = create_config_folder(root=omd_root, relays=[relay_id])
    handled_task = get_task_handler.process(relay_id=relay_id, task_id=task.id)
    assert handled_task == task


@pytest.mark.usefixtures("site_context")
def test_get_task_handler_with_unknown_task(
    get_task_handler: GetRelayTaskHandler,
    populated_repos: tuple[RelayID, RelayTask, RelaysRepository, TasksRepository],
) -> None:
    relay_id, task, relays_repository, tasks_repository = populated_repos

    with pytest.raises(TaskNotFoundError):
        get_task_handler.process(
            relay_id=relay_id,
            task_id=TaskID("unknown-task-id"),
        )


def test_get_tasks_handler(
    get_tasks_handler: GetRelayTasksHandler,
    populated_repos: tuple[RelayID, RelayTask, RelaysRepository, TasksRepository],
    omd_root: Path,
) -> None:
    relay_id, task, relays_repository, tasks_repository = populated_repos
    _ = create_config_folder(root=omd_root, relays=[relay_id])

    handled_tasks = get_tasks_handler.process(relay_id=relay_id, status=None, relay_serial=SERIAL)
    assert handled_tasks == [task]


def test_get_tasks_handler_with_filter(
    get_tasks_handler: GetRelayTasksHandler,
    populated_repos: tuple[RelayID, RelayTask, RelaysRepository, TasksRepository],
    omd_root: Path,
) -> None:
    relay_id, task, relays_repository, tasks_repository = populated_repos
    _ = create_config_folder(root=omd_root, relays=[relay_id])
    handled_tasks = get_tasks_handler.process(
        relay_id=relay_id, status=TaskStatus.FINISHED, relay_serial=SERIAL
    )
    assert handled_tasks == []
