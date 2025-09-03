#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated

import fastapi

from cmk.agent_receiver.relay.api.dependencies.relays_repository import get_relays_repository
from cmk.agent_receiver.relay.api.routers.tasks.handlers import (
    CreateTaskHandler,
    GetRelayTaskHandler,
    GetRelayTasksHandler,
    UpdateTaskHandler,
)
from cmk.agent_receiver.relay.api.routers.tasks.libs.tasks_repository import TasksRepository
from cmk.agent_receiver.relay.lib.relay_config import RelayConfig
from cmk.agent_receiver.relay.lib.relays_repository import RelaysRepository


def get_relay_config() -> RelayConfig:
    return RelayConfig.load()


def get_tasks_repository(
    config: Annotated[RelayConfig, fastapi.Depends(get_relay_config)],
) -> TasksRepository:
    return TasksRepository(ttl_seconds=config.task_ttl)


def get_relay_tasks_handler(
    tasks_repository: Annotated[TasksRepository, fastapi.Depends(get_tasks_repository)],
    relays_repository: Annotated[RelaysRepository, fastapi.Depends(get_relays_repository)],
) -> GetRelayTasksHandler:
    return GetRelayTasksHandler(
        tasks_repository=tasks_repository,
        relay_repository=relays_repository,
    )


def get_relay_task_handler(
    tasks_repository: Annotated[TasksRepository, fastapi.Depends(get_tasks_repository)],
    relays_repository: Annotated[RelaysRepository, fastapi.Depends(get_relays_repository)],
) -> GetRelayTaskHandler:
    return GetRelayTaskHandler(
        tasks_repository=tasks_repository,
        relay_repository=relays_repository,
    )


def get_create_task_handler(
    tasks_repository: Annotated[TasksRepository, fastapi.Depends(get_tasks_repository)],
    relays_repository: Annotated[RelaysRepository, fastapi.Depends(get_relays_repository)],
) -> CreateTaskHandler:
    return CreateTaskHandler(
        tasks_repository=tasks_repository,
        relays_repository=relays_repository,
    )


def get_update_task_handler(
    tasks_repository: Annotated[TasksRepository, fastapi.Depends(get_tasks_repository)],
    relays_repository: Annotated[RelaysRepository, fastapi.Depends(get_relays_repository)],
) -> UpdateTaskHandler:
    return UpdateTaskHandler(
        tasks_repository=tasks_repository,
        relays_repository=relays_repository,
    )
