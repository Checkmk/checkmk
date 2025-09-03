#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Comprehensive unit tests for TimedTaskStore class."""

import time
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from cmk.agent_receiver.relay.api.routers.tasks.libs.tasks_repository import (
    ResultType,
    Task,
    TasksRepository,
    TaskStatus,
    TaskType,
)
from cmk.agent_receiver.relay.lib.shared_types import TaskID


def test_setitem_and_getitem_basic_functionality():
    """Test adding and retrieving a task."""
    store = TasksRepository.TimedTaskStore(ttl_seconds=300.0)
    task_id = TaskID("test-task-1")
    task = Task(
        type=TaskType.FETCH_AD_HOC,
        payload="test payload",
        creation_timestamp=datetime.now(),
        update_timestamp=datetime.now(),
        id=task_id,
    )

    store[task_id] = task
    retrieved_task = store[task_id]

    assert retrieved_task == task
    assert retrieved_task.payload == "test payload"
    assert retrieved_task.type == TaskType.FETCH_AD_HOC


def test_setitem_updates_existing_task():
    """Test updating an existing task in the store."""
    store = TasksRepository.TimedTaskStore(ttl_seconds=300.0)
    task_id = TaskID("test-task-1")
    original_task = Task(
        type=TaskType.FETCH_AD_HOC,
        payload="original payload",
        creation_timestamp=datetime.now(),
        update_timestamp=datetime.now(),
        id=task_id,
    )

    store[task_id] = original_task
    now = datetime.now() + timedelta(seconds=1)

    updated_task = Task(
        type=TaskType.RELAY_CONFIG,
        payload="updated payload",
        creation_timestamp=now,
        update_timestamp=now,
        status=TaskStatus.FINISHED,
        id=task_id,
    )

    store[task_id] = updated_task
    retrieved_task = store[task_id]

    assert retrieved_task == updated_task
    assert retrieved_task.payload == "updated payload"
    assert retrieved_task.status == TaskStatus.FINISHED


def test_getitem_raises_keyerror_for_nonexistent_task():
    """Test that retrieving non-existent task raises KeyError."""
    store = TasksRepository.TimedTaskStore(ttl_seconds=300.0)

    with pytest.raises(KeyError):
        _ = store[TaskID("non-existent")]


def test_contains_returns_true_for_existing_task():
    """Test __contains__ method returns True for existing tasks."""
    store = TasksRepository.TimedTaskStore(ttl_seconds=300.0)
    task_id = TaskID("test-task")
    task = Task(
        type=TaskType.FETCH_AD_HOC,
        payload="test payload",
        creation_timestamp=datetime.now(),
        update_timestamp=datetime.now(),
        id=task_id,
    )

    store[task_id] = task

    assert task_id in store


def test_contains_returns_false_for_nonexistent_task():
    """Test __contains__ method returns False for non-existent tasks."""
    store = TasksRepository.TimedTaskStore(ttl_seconds=300.0)

    assert TaskID("non-existent") not in store


def test_values_returns_all_tasks():
    """Test values method returns all non-expired tasks."""
    store = TasksRepository.TimedTaskStore(ttl_seconds=300.0)

    tasks = []
    for i in range(3):
        task_id = TaskID(f"task-{i}")
        task = Task(
            type=TaskType.FETCH_AD_HOC,
            payload=f"payload {i}",
            creation_timestamp=datetime.now(),
            update_timestamp=datetime.now(),
            id=task_id,
        )
        tasks.append(task)
        store[task_id] = task

    values = store.values()

    assert len(values) == 3
    assert all(task in values for task in tasks)


def test_values_returns_empty_list_for_empty_store():
    """Test values method returns empty list when store is empty."""
    store = TasksRepository.TimedTaskStore(ttl_seconds=300.0)

    assert store.values() == []


def test_expired_tasks_are_automatically_removed():
    """Test that expired tasks are automatically cleaned up during access operations."""
    store = TasksRepository.TimedTaskStore(ttl_seconds=0.1)

    # Add a task
    task_id = TaskID("test-task")
    task = Task(
        type=TaskType.FETCH_AD_HOC,
        payload="test payload",
        creation_timestamp=datetime.now(),
        update_timestamp=datetime.now(),
        id=task_id,
    )
    store[task_id] = task

    # Verify task exists
    assert task_id in store

    # Wait for expiration
    time.sleep(0.2)

    # Task should be expired and automatically removed
    assert task_id not in store
    assert not store.values()


def test_expired_tasks_removed_on_getitem():
    """Test that expired tasks are removed when accessing other tasks."""
    store = TasksRepository.TimedTaskStore(ttl_seconds=0.1)

    # Add two tasks
    expired_task_id = TaskID("expired-task")
    expired_task = Task(
        type=TaskType.FETCH_AD_HOC,
        payload="expired",
        creation_timestamp=datetime.now(),
        update_timestamp=datetime.now(),
        id=expired_task_id,
    )
    store[expired_task_id] = expired_task

    # Wait for first task to expire
    time.sleep(0.2)

    # Add fresh task
    fresh_task_id = TaskID("fresh-task")
    fresh_task = Task(
        type=TaskType.FETCH_AD_HOC,
        payload="fresh",
        creation_timestamp=datetime.now(),
        update_timestamp=datetime.now(),
        id=fresh_task_id,
    )
    store[fresh_task_id] = fresh_task

    # Access fresh task - should trigger cleanup
    result = store[fresh_task_id]

    # Expired task should be gone, fresh task should remain
    assert expired_task_id not in store
    assert fresh_task_id in store
    assert result == fresh_task


def test_expired_tasks_removed_on_values():
    """Test that expired tasks are removed when calling values()."""
    store = TasksRepository.TimedTaskStore(ttl_seconds=0.1)

    # Add task that will expire
    expired_task_id = TaskID("expired-task")
    expired_task = Task(
        type=TaskType.FETCH_AD_HOC,
        payload="expired",
        creation_timestamp=datetime.now(),
        update_timestamp=datetime.now(),
        id=expired_task_id,
    )
    store[expired_task_id] = expired_task

    # Wait for expiration
    time.sleep(0.2)

    # Add fresh task
    fresh_task_id = TaskID("fresh-task")
    fresh_task = Task(
        type=TaskType.FETCH_AD_HOC,
        payload="fresh",
        creation_timestamp=datetime.now(),
        update_timestamp=datetime.now(),
        id=fresh_task_id,
    )
    store[fresh_task_id] = fresh_task

    # Get all values - should trigger cleanup
    values = store.values()

    # Should only return fresh task
    assert len(values) == 1
    assert values[0] == fresh_task
    assert expired_task_id not in store
    assert fresh_task_id in store


def test_expired_tasks_removed_on_contains():
    """Test that expired tasks are removed when checking membership."""
    store = TasksRepository.TimedTaskStore(ttl_seconds=0.1)

    # Add task that will expire
    task_id = TaskID("expired-task")
    task = Task(
        type=TaskType.FETCH_AD_HOC,
        payload="expired",
        creation_timestamp=datetime.now(),
        update_timestamp=datetime.now(),
        id=task_id,
    )
    store[task_id] = task

    # Wait for expiration
    time.sleep(0.2)

    # Check if expired task exists - should trigger cleanup
    result = task_id in store

    # Should return False and task should be removed
    assert result is False


def test_multiple_expired_tasks_cleanup():
    """Test cleanup removes multiple expired tasks at once."""
    store = TasksRepository.TimedTaskStore(ttl_seconds=0.1)

    # Add multiple tasks that will expire
    expired_task_ids = []
    for i in range(3):
        task_id = TaskID(f"expired-task-{i}")
        expired_task_ids.append(task_id)
        task = Task(
            type=TaskType.FETCH_AD_HOC,
            payload=f"expired {i}",
            creation_timestamp=datetime.now(),
            update_timestamp=datetime.now(),
            id=task_id,
        )
        store[task_id] = task

    # Wait for expiration
    time.sleep(0.2)

    # Add fresh task
    fresh_task_id = TaskID("fresh-task")
    fresh_task = Task(
        type=TaskType.FETCH_AD_HOC,
        payload="fresh",
        creation_timestamp=datetime.now(),
        update_timestamp=datetime.now(),
        id=fresh_task_id,
    )
    store[fresh_task_id] = fresh_task

    # Get values to trigger cleanup
    values = store.values()

    # All expired tasks should be removed, only fresh task remains
    assert len(values) == 1
    assert values[0] == fresh_task
    for expired_id in expired_task_ids:
        assert expired_id not in store
    assert fresh_task_id in store


def test_task_with_all_result_types():
    """Test storing tasks with different result types."""
    store = TasksRepository.TimedTaskStore(ttl_seconds=300.0)

    # Task with OK result
    ok_task_id = TaskID("ok-task")
    ok_task = Task(
        type=TaskType.FETCH_AD_HOC,
        payload="test",
        creation_timestamp=datetime.now(),
        update_timestamp=datetime.now(),
        result_type=ResultType.OK,
        result_payload="success data",
        status=TaskStatus.FINISHED,
        id=ok_task_id,
    )

    # Task with ERROR result
    error_task_id = TaskID("error-task")
    error_task = Task(
        type=TaskType.RELAY_CONFIG,
        payload="test",
        creation_timestamp=datetime.now(),
        update_timestamp=datetime.now(),
        result_type=ResultType.ERROR,
        result_payload="error message",
        status=TaskStatus.FAILED,
        id=error_task_id,
    )

    # Task with no result (pending)
    pending_task_id = TaskID("pending-task")
    pending_task = Task(
        type=TaskType.FETCH_AD_HOC,
        payload="test",
        creation_timestamp=datetime.now(),
        update_timestamp=datetime.now(),
        id=pending_task_id,
    )

    store[ok_task_id] = ok_task
    store[error_task_id] = error_task
    store[pending_task_id] = pending_task

    # All tasks should be stored correctly
    assert store[ok_task_id].result_type == ResultType.OK
    assert store[error_task_id].result_type == ResultType.ERROR
    assert store[pending_task_id].result_type is None
    assert len(store.values()) == 3


def test_task_with_different_task_types():
    """Test storing tasks with different task types."""
    store = TasksRepository.TimedTaskStore(ttl_seconds=300.0)

    # FETCH_AD_HOC task
    fetch_task_id = TaskID("fetch-task")
    fetch_task = Task(
        type=TaskType.FETCH_AD_HOC,
        payload="fetch payload",
        creation_timestamp=datetime.now(),
        update_timestamp=datetime.now(),
        id=fetch_task_id,
    )

    # RELAY_CONFIG task
    config_task_id = TaskID("config-task")
    config_task = Task(
        type=TaskType.RELAY_CONFIG,
        payload="config payload",
        creation_timestamp=datetime.now(),
        update_timestamp=datetime.now(),
        id=config_task_id,
    )

    store[fetch_task_id] = fetch_task
    store[config_task_id] = config_task

    assert store[fetch_task_id].type == TaskType.FETCH_AD_HOC
    assert store[config_task_id].type == TaskType.RELAY_CONFIG


def test_task_with_different_statuses():
    """Test storing tasks with different status values."""
    store = TasksRepository.TimedTaskStore(ttl_seconds=300.0)

    # PENDING task (default)
    pending_task_id = TaskID("pending-task")
    pending_task = Task(
        type=TaskType.FETCH_AD_HOC,
        payload="pending",
        creation_timestamp=datetime.now(),
        update_timestamp=datetime.now(),
        id=pending_task_id,
    )

    # FINISHED task
    finished_task_id = TaskID("finished-task")
    finished_task = Task(
        type=TaskType.FETCH_AD_HOC,
        payload="finished",
        creation_timestamp=datetime.now(),
        update_timestamp=datetime.now(),
        status=TaskStatus.FINISHED,
        id=finished_task_id,
    )

    # FAILED task
    failed_task_id = TaskID("failed-task")
    failed_task = Task(
        type=TaskType.FETCH_AD_HOC,
        payload="failed",
        creation_timestamp=datetime.now(),
        update_timestamp=datetime.now(),
        status=TaskStatus.FAILED,
        id=failed_task_id,
    )

    store[pending_task_id] = pending_task
    store[finished_task_id] = finished_task
    store[failed_task_id] = failed_task

    assert store[pending_task_id].status == TaskStatus.PENDING
    assert store[finished_task_id].status == TaskStatus.FINISHED
    assert store[failed_task_id].status == TaskStatus.FAILED


def test_expiration_based_on_update_timestamp():
    """Test that expiration is based on update_timestamp, not creation_timestamp."""
    store = TasksRepository.TimedTaskStore(ttl_seconds=0.2)

    # Create task with old creation_timestamp but recent update_timestamp
    old_time = datetime.now() - timedelta(seconds=1)
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

    # Wait for expiration based on update_timestamp
    time.sleep(0.3)

    # Now task should be expired
    assert task_id not in store


@patch("cmk.agent_receiver.relay.api.routers.tasks.libs.tasks_repository.logger")
def test_logging_during_cleanup(mock_logger):
    """Test that cleanup operations are logged properly."""
    store = TasksRepository.TimedTaskStore(ttl_seconds=0.1)

    # Add task that will expire
    task_id = TaskID("test-task")
    task = Task(
        type=TaskType.FETCH_AD_HOC,
        payload="test",
        creation_timestamp=datetime.now(),
        update_timestamp=datetime.now(),
        id=task_id,
    )
    store[task_id] = task

    # Wait for expiration
    time.sleep(0.2)

    # Trigger cleanup by accessing store
    _ = store.values()

    # Verify logging occurred
    mock_logger.debug.assert_called()
    # Check that the expired task ID was logged
    logged_args = mock_logger.debug.call_args[0]
    assert "Expiring Tasks:" in logged_args[0]
    assert task_id in logged_args[1]
