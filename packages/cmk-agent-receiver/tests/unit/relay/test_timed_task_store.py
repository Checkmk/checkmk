#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
from collections.abc import Iterator
from datetime import datetime, timedelta

import pytest
from time_machine import Coordinates, travel

from cmk.agent_receiver.relay.api.routers.tasks.libs.tasks_repository import (
    Task,
    TaskType,
    TimedTaskStore,
)
from cmk.agent_receiver.relay.lib.shared_types import TaskID


def _make_task(task_id: TaskID, now: datetime | None = None) -> Task:
    now = now or datetime.now()
    return Task(
        type=TaskType.FETCH_AD_HOC,
        payload="test payload",
        creation_timestamp=now,
        update_timestamp=now,
        id=task_id,
    )


TTL = 300
SHIFT_TO_EXPIRE = TTL + 10


@pytest.fixture
def store() -> TimedTaskStore:
    return TimedTaskStore(ttl_seconds=TTL)


@pytest.fixture
def time() -> Iterator[Coordinates]:
    with travel(datetime.now()) as traveler:
        yield traveler


def test_setitem_and_getitem_basic_functionality(store: TimedTaskStore) -> None:
    task_id = TaskID("test-task-1")
    task = _make_task(task_id)
    store[task_id] = task
    assert id(store[task_id]) == id(task)


def test_setitem_updates_existing_task(store: TimedTaskStore) -> None:
    task_id = TaskID("test-task-1")
    store[task_id] = _make_task(task_id)

    updated_task = _make_task(task_id)
    store[task_id] = updated_task
    assert id(store[task_id]) == id(updated_task)


def test_getitem_raises_keyerror_for_nonexistent_task(store: TimedTaskStore) -> None:
    with pytest.raises(KeyError):
        _ = store[TaskID("non-existent")]


def test_contains_returns_true_for_existing_task(store: TimedTaskStore) -> None:
    task_id = TaskID("test-task")
    task = _make_task(task_id)
    store[task_id] = task
    assert task_id in store


def test_contains_returns_false_for_nonexistent_task(store: TimedTaskStore) -> None:
    assert TaskID("non-existent") not in store


def test_values_returns_all_tasks(store: TimedTaskStore) -> None:
    tasks: list[Task] = []
    for i in range(3):
        task_id = TaskID(f"task-{i}")
        tasks.append(_make_task(task_id))
        store[task_id] = tasks[-1]
    values = store.values()
    assert len(values) == 3
    assert all(task in values for task in tasks)


def test_values_returns_empty_list_for_empty_store(store: TimedTaskStore) -> None:
    assert store.values() == []


def test_expired_tasks_removed_on_getitem(
    time: Coordinates,
    store: TimedTaskStore,
) -> None:
    expired_task_id = TaskID("expired-task")
    store[expired_task_id] = _make_task(expired_task_id)
    time.shift(SHIFT_TO_EXPIRE)
    assert expired_task_id not in store


def test_expired_tasks_removed_on_values(time: Coordinates, store: TimedTaskStore) -> None:
    expired_task_id = TaskID("expired-task")
    store[expired_task_id] = _make_task(expired_task_id)
    time.shift(SHIFT_TO_EXPIRE)
    assert len(store.values()) == 0


def test_expired_tasks_removed_on_contains(time: Coordinates, store: TimedTaskStore) -> None:
    task_id = TaskID("expired-task")
    store[task_id] = _make_task(task_id)
    time.shift(SHIFT_TO_EXPIRE)
    assert task_id not in store


def test_multiple_expired_tasks_cleanup(time: Coordinates, store: TimedTaskStore) -> None:
    for i in range(3):
        task_id = TaskID(f"expired-task-{i}")
        store[task_id] = _make_task(task_id)
    time.shift(SHIFT_TO_EXPIRE)

    fresh_task_id = TaskID("fresh-task")
    store[fresh_task_id] = _make_task(fresh_task_id)

    # All expired tasks should be removed, only fresh task remains
    assert len(store.values()) == 1
    assert fresh_task_id in store


def test_expiration_based_on_update_timestamp(time: Coordinates, store: TimedTaskStore) -> None:
    # Create task with old creation_timestamp but recent update_timestamp
    old_time = datetime.now() - timedelta(seconds=SHIFT_TO_EXPIRE)
    recent_time = datetime.now()

    task_id = TaskID("test-task")
    task = Task(
        type=TaskType.FETCH_AD_HOC,
        payload="test",
        creation_timestamp=old_time,  # Old creation time
        update_timestamp=recent_time,  # Recent update time
        id=task_id,
    )

    store[task_id] = task

    # Task should still exist because update_timestamp is recent
    assert task_id in store
    time.shift(SHIFT_TO_EXPIRE)
    assert task_id not in store


def test_logging_during_cleanup(
    caplog: pytest.LogCaptureFixture, time: Coordinates, store: TimedTaskStore
) -> None:
    caplog.set_level(logging.DEBUG, logger="agent-receiver")
    task_id = TaskID("test-task")
    store[task_id] = _make_task(task_id)
    time.shift(SHIFT_TO_EXPIRE)

    # Trigger cleanup by accessing store
    _ = store.values()

    assert len(caplog.records) > 0, caplog.records
    assert "Expiring Tasks:" in caplog.records[0].getMessage()
    assert task_id in caplog.records[1].getMessage()
