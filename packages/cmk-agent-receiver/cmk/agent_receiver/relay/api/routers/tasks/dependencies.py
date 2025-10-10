#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated

import fastapi

from cmk.agent_receiver.config import Config, get_config
from cmk.agent_receiver.relay.api.dependencies.relays_repository import get_relays_repository
from cmk.agent_receiver.relay.api.routers.tasks.handlers import (
    ActivateConfigHandler,
    CreateTaskHandler,
    GetRelayTaskHandler,
    GetRelayTasksHandler,
    UpdateTaskHandler,
)
from cmk.agent_receiver.relay.api.routers.tasks.libs.config_task_factory import ConfigTaskFactory
from cmk.agent_receiver.relay.api.routers.tasks.libs.tasks_repository import TasksRepository
from cmk.agent_receiver.relay.lib.relays_repository import RelaysRepository


def get_tasks_repository(
    config: Annotated[Config, fastapi.Depends(get_config)],
) -> TasksRepository:
    return TasksRepository(
        ttl_seconds=config.task_ttl,
        max_tasks_per_relay=config.max_tasks_per_relay,
    )


def get_config_task_factory(
    tasks_repository: Annotated[TasksRepository, fastapi.Depends(get_tasks_repository)],
    relays_repository: Annotated[RelaysRepository, fastapi.Depends(get_relays_repository)],
) -> ConfigTaskFactory:
    return ConfigTaskFactory(
        tasks_repository=tasks_repository,
        relays_repository=relays_repository,
    )


def get_relay_tasks_handler(
    tasks_repository: Annotated[TasksRepository, fastapi.Depends(get_tasks_repository)],
    relays_repository: Annotated[RelaysRepository, fastapi.Depends(get_relays_repository)],
    config_task_factory: Annotated[ConfigTaskFactory, fastapi.Depends(get_config_task_factory)],
) -> GetRelayTasksHandler:
    _ = config_task_factory
    return GetRelayTasksHandler(
        tasks_repository=tasks_repository,
        relay_repository=relays_repository,
        config_task_factory=config_task_factory,
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
) -> CreateTaskHandler:
    return CreateTaskHandler(
        tasks_repository=tasks_repository,
    )


def get_update_task_handler(
    tasks_repository: Annotated[TasksRepository, fastapi.Depends(get_tasks_repository)],
    relays_repository: Annotated[RelaysRepository, fastapi.Depends(get_relays_repository)],
) -> UpdateTaskHandler:
    return UpdateTaskHandler(
        tasks_repository=tasks_repository,
        relays_repository=relays_repository,
    )


def get_activate_config_handler(
    config_task_factory: Annotated[ConfigTaskFactory, fastapi.Depends(get_config_task_factory)],
) -> ActivateConfigHandler:
    return ActivateConfigHandler(
        config_task_factory=config_task_factory,
    )
