#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

import dataclasses
import uuid
from datetime import datetime, UTC
from enum import StrEnum
from typing import final

from cmk.agent_receiver.log import logger
from cmk.agent_receiver.relay.lib.shared_types import (
    RelayID,
    TaskID,
    TaskNotFoundError,
    TooManyTasksError,
)


class TaskStatus(StrEnum):
    PENDING = "PENDING"
    FINISHED = "FINISHED"
    FAILED = "FAILED"


class TaskType(StrEnum):
    RELAY_CONFIG = "RELAY_CONFIG"
    FETCH_AD_HOC = "FETCH_AD_HOC"


class ResultType(StrEnum):
    OK = "OK"
    ERROR = "ERROR"


@dataclasses.dataclass(frozen=True, slots=True)
class FetchSpec:
    payload: str
    timeout: float


@dataclasses.dataclass(frozen=True, slots=True)
class RelayConfigSpec:
    serial: str
    tar_data: bytes


Spec = FetchSpec | RelayConfigSpec


@dataclasses.dataclass(frozen=True, slots=True, kw_only=True)
class RelayTask:
    spec: Spec
    creation_timestamp: datetime
    update_timestamp: datetime
    result_type: ResultType | None = None
    result_payload: str | None = None
    status: TaskStatus = TaskStatus.PENDING
    id: TaskID = dataclasses.field(default_factory=lambda: TaskID(str(uuid.uuid4())))


# Persistence layer is not thread safe yet.
# Note: Since we are using async endpoints in the agent-receiver
# the executions are added as a coroutine to the main async event loop.
# The persistence layer is for now an in memory dict so we won't need
# to make this thread-safe as this should not be accessed by multiple threads
# concurrently.
GLOBAL_TASKS: dict[RelayID, TimedTaskStore] = {}


@dataclasses.dataclass(slots=True, frozen=True)
class TasksRepository:
    ttl_seconds: float
    max_tasks_per_relay: int

    def __post_init__(self) -> None:
        if self.ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be greater than 0")

    def _get_or_create_storage(self, relay_id: RelayID) -> TimedTaskStore:
        """Get or create a _TimedTaskStore for the given relay."""
        if relay_id not in GLOBAL_TASKS:
            GLOBAL_TASKS[relay_id] = TimedTaskStore(ttl_seconds=self.ttl_seconds)
        return GLOBAL_TASKS[relay_id]

    def get_tasks(self, relay_id: RelayID) -> list[RelayTask]:
        try:
            tasks = GLOBAL_TASKS[relay_id]
            # _TimedTaskStore automatically handles expiration when calling values()
            return tasks.values()
        except KeyError:
            logger.warning("Relay with ID %s not found", relay_id)
            return []

    def get_task(self, relay_id: RelayID, task_id: TaskID) -> RelayTask:
        try:
            return GLOBAL_TASKS[relay_id][task_id]
        except KeyError:
            raise TaskNotFoundError(task_id)

    def store_task(self, relay_id: RelayID, task: RelayTask) -> RelayTask:
        tasks = self._get_or_create_storage(relay_id)
        if len(tasks) >= self.max_tasks_per_relay:
            raise TooManyTasksError(self.max_tasks_per_relay)
        tasks[task.id] = task
        return task

    def update_task(
        self,
        *,
        relay_id: RelayID,
        task_id: TaskID,
        result_type: ResultType,
        result_payload: str,
        status: TaskStatus,
    ) -> RelayTask:
        try:
            task = GLOBAL_TASKS[relay_id][task_id]
        except KeyError as exc:
            logger.warning("Relay %s: Task with ID %s not found", relay_id, task_id)
            raise TaskNotFoundError(task_id) from exc

        new_task = dataclasses.replace(
            task,
            result_type=result_type,
            result_payload=result_payload,
            status=status,
            update_timestamp=datetime.now(UTC),
        )
        GLOBAL_TASKS[relay_id][task_id] = new_task
        return new_task


@final
class TimedTaskStore:
    """Custom store implementation that uses Task's update_timestamp for expiration."""

    def __init__(self, ttl_seconds: float):
        self.ttl_seconds = ttl_seconds
        self._tasks: dict[TaskID, RelayTask] = {}

    def _is_expired(self, task: RelayTask) -> bool:
        """Check if a task has expired based on its update_timestamp."""
        now = datetime.now(UTC)
        return (now - task.update_timestamp).total_seconds() > self.ttl_seconds

    def _cleanup_expired(self) -> None:
        """Remove expired tasks from the store."""
        expired_task_ids = [
            task_id for task_id, task in self._tasks.items() if self._is_expired(task)
        ]
        logger.debug("Expiring Tasks: %s", expired_task_ids)

        for task_id in expired_task_ids:
            del self._tasks[task_id]

    def __getitem__(self, key: TaskID) -> RelayTask:
        self._cleanup_expired()
        return self._tasks[key]

    def __setitem__(self, key: TaskID, value: RelayTask) -> None:
        self._cleanup_expired()
        self._tasks[key] = value

    def values(self) -> list[RelayTask]:
        """Return all non-expired tasks."""
        self._cleanup_expired()
        return list(self._tasks.values())

    def __contains__(self, key: TaskID) -> bool:
        self._cleanup_expired()
        return key in self._tasks

    def __len__(self) -> int:
        return len(self._tasks)
