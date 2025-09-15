#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_receiver.relay.api.routers.tasks.handlers.create_task import (
    CreateTaskHandler,
)
from cmk.agent_receiver.relay.api.routers.tasks.libs.tasks_repository import (
    TasksRepository,
    TaskType,
)
from cmk.agent_receiver.relay.lib.relays_repository import RelaysRepository
from cmk.agent_receiver.relay.lib.shared_types import RelayID, RelayNotFoundError
from cmk.agent_receiver.relay.lib.site_auth import InternalAuth


@pytest.mark.usefixtures("site_context")
def test_process_create_task(
    create_task_handler: CreateTaskHandler,
    relays_repository: RelaysRepository,
    tasks_repository: TasksRepository,
    test_user: InternalAuth,
) -> None:
    # arrange
    task_type = TaskType.FETCH_AD_HOC
    task_payload = '{"url": "http://example.com/data"}'

    # Register a relay first
    relay_id = relays_repository.add_relay(test_user, alias="test-relay")

    # act
    task_id = create_task_handler.process(
        relay_id=relay_id,
        task_type=task_type,
        task_payload=task_payload,
    )

    # assert
    tasks_enqueued = tasks_repository.get_tasks(relay_id)
    assert len(tasks_enqueued) == 1
    assert tasks_enqueued[0].id == task_id
    assert tasks_enqueued[0].type == task_type
    assert tasks_enqueued[0].payload == task_payload


@pytest.mark.usefixtures("site_context")
def test_process_create_task_non_existent_relay(create_task_handler: CreateTaskHandler) -> None:
    # arrange
    relay_id = RelayID("non-existent-relay-id")

    # act
    with pytest.raises(RelayNotFoundError):
        create_task_handler.process(
            relay_id=relay_id,
            task_type=TaskType.FETCH_AD_HOC,
            task_payload="any payload",
        )


def test_tasks_repository_ttl_validation() -> None:
    """Test that TasksRepository validates TTL is greater than 0."""
    # Test zero TTL raises ValueError
    with pytest.raises(ValueError, match="ttl_seconds must be greater than 0"):
        TasksRepository(ttl_seconds=0.0, max_tasks_per_relay=5)

    # Test negative TTL raises ValueError
    with pytest.raises(ValueError, match="ttl_seconds must be greater than 0"):
        TasksRepository(ttl_seconds=-1.0, max_tasks_per_relay=5)

    # Test positive TTL works
    repository = TasksRepository(ttl_seconds=120.0, max_tasks_per_relay=5)
    assert repository.ttl_seconds == 120.0
