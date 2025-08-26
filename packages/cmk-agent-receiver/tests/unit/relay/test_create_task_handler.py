#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import uuid
from collections.abc import Iterator

import pytest

from cmk.agent_receiver.relay.api.routers.tasks.handlers.create_task import (
    CreateTaskHandler,
    RelayNotFoundError,
)
from cmk.agent_receiver.relay.api.routers.tasks.libs.tasks_repository import (
    TasksRepository,
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
def create_task_handler(
    tasks_repository: TasksRepository, relays_repository: RelaysRepository
) -> Iterator[CreateTaskHandler]:
    handler = CreateTaskHandler(
        tasks_repository=tasks_repository, relays_repository=relays_repository
    )
    yield handler


def test_process_create_task(
    create_task_handler: CreateTaskHandler,
    relays_repository: RelaysRepository,
) -> None:
    # arrange

    # Let's register a relay
    relay_id = RelayID(str(uuid.uuid4()))
    relays_repository.add_relay(relay_id)

    # act
    create_task_handler.process(relay_id=relay_id)

    # assert (no exception expected)


def test_process_create_task_non_existent_relay(create_task_handler: CreateTaskHandler) -> None:
    # arrange
    relay_id = RelayID(str(uuid.uuid4()))  # Any, non existent

    # act
    with pytest.raises(RelayNotFoundError):
        create_task_handler.process(relay_id=relay_id)
