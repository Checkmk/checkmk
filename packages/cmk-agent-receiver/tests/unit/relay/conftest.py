#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import uuid
from collections.abc import Iterator
from datetime import datetime, UTC
from http import HTTPStatus
from pathlib import Path

import httpx
import pytest
from pydantic import SecretStr

from cmk.agent_receiver.config import Config
from cmk.agent_receiver.relay.api.routers.relays.handlers.register_relay import (
    RegisterRelayHandler,
)
from cmk.agent_receiver.relay.api.routers.relays.handlers.unregister_relay import (
    UnregisterRelayHandler,
)
from cmk.agent_receiver.relay.api.routers.tasks.handlers import (
    GetRelayTaskHandler,
    GetRelayTasksHandler,
)
from cmk.agent_receiver.relay.api.routers.tasks.handlers.create_task import (
    CreateTaskHandler,
)
from cmk.agent_receiver.relay.api.routers.tasks.handlers.update_task import (
    UpdateTaskHandler,
)
from cmk.agent_receiver.relay.api.routers.tasks.libs.tasks_repository import (
    FetchSpec,
    RelayTask,
    TasksRepository,
)
from cmk.agent_receiver.relay.lib.relays_repository import RelaysRepository
from cmk.agent_receiver.relay.lib.shared_types import RelayID, TaskID
from cmk.agent_receiver.relay.lib.site_auth import UserAuth


def create_relay_mock_transport() -> httpx.MockTransport:
    """Create a stateful mock transport for relay operations."""
    registered_relays = set()

    def handler(request: httpx.Request) -> httpx.Response:
        # Create relay
        if request.method == "POST" and request.url.path.endswith(
            "/domain-types/relay/collections/all"
        ):
            relay_id = str(uuid.uuid4())
            registered_relays.add(relay_id)
            return httpx.Response(HTTPStatus.OK, json={"id": relay_id})

        # Check/Get relay
        elif request.method == "GET" and "/objects/relay/" in request.url.path:
            relay_id = request.url.path.split("/")[-1]
            if relay_id in registered_relays:
                return httpx.Response(HTTPStatus.OK, json={"id": relay_id})
            return httpx.Response(HTTPStatus.NOT_FOUND, json={"error": "Relay not found"})

        # Delete relay
        elif request.method == "DELETE" and "/objects/relay/" in request.url.path:
            relay_id = request.url.path.split("/")[-1]
            if relay_id in registered_relays:
                registered_relays.remove(relay_id)
                return httpx.Response(HTTPStatus.NO_CONTENT)
            return httpx.Response(HTTPStatus.NOT_FOUND, json={"error": "Relay not found"})

        # Unhandled request
        return httpx.Response(HTTPStatus.NOT_FOUND, json={"error": "Endpoint not found"})

    return httpx.MockTransport(handler)


def create_test_relays_repository() -> RelaysRepository:
    """Create a RelaysRepository configured with mock transport for testing."""
    client = httpx.Client(
        base_url="http://test.com/test/check_mk/api/1.0",
        headers={"Content-Type": "application/json"},
        transport=create_relay_mock_transport(),
    )
    return RelaysRepository(client, siteid="test-site")


@pytest.fixture
def site_context(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Config:
    site_id = "NO_SITE"
    site_dir = tmp_path / site_id
    site_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("OMD_ROOT", str(site_dir))
    monkeypatch.setenv("OMD_SITE", site_id)
    site_context = Config()
    site_context.internal_secret_path.parent.mkdir(parents=True, exist_ok=True)
    site_context.internal_secret_path.write_text("lol")
    return site_context


@pytest.fixture()
def test_user() -> UserAuth:
    return UserAuth(SecretStr("Bearer test-token"))


@pytest.fixture()
def relays_repository() -> Iterator[RelaysRepository]:
    """Provides a RelaysRepository with mock transport for testing."""
    repository = create_test_relays_repository()
    yield repository


@pytest.fixture()
def tasks_repository() -> Iterator[TasksRepository]:
    """Provides a TasksRepository for testing."""
    repository = TasksRepository(ttl_seconds=10, max_tasks_per_relay=5)
    yield repository


@pytest.fixture()
def register_relay_handler(relays_repository: RelaysRepository) -> Iterator[RegisterRelayHandler]:
    """Provides a RegisterRelayHandler with mock dependencies."""
    handler = RegisterRelayHandler(relays_repository=relays_repository)
    yield handler


@pytest.fixture()
def unregister_relay_handler(
    relays_repository: RelaysRepository,
) -> Iterator[UnregisterRelayHandler]:
    """Provides an UnregisterRelayHandler with mock dependencies."""
    handler = UnregisterRelayHandler(relays_repository=relays_repository)
    yield handler


@pytest.fixture()
def create_task_handler(
    tasks_repository: TasksRepository, relays_repository: RelaysRepository
) -> Iterator[CreateTaskHandler]:
    """Provides a CreateTaskHandler with mock dependencies."""
    handler = CreateTaskHandler(
        tasks_repository=tasks_repository, relays_repository=relays_repository
    )
    yield handler


@pytest.fixture()
def update_task_handler(
    tasks_repository: TasksRepository, relays_repository: RelaysRepository
) -> Iterator[UpdateTaskHandler]:
    """Provides an UpdateTaskHandler with mock dependencies."""
    handler = UpdateTaskHandler(
        tasks_repository=tasks_repository, relays_repository=relays_repository
    )
    yield handler


@pytest.fixture()
def get_task_handler(
    tasks_repository: TasksRepository, relays_repository: RelaysRepository
) -> Iterator[GetRelayTaskHandler]:
    handler = GetRelayTaskHandler(
        tasks_repository=tasks_repository, relay_repository=relays_repository
    )
    yield handler


@pytest.fixture()
def get_tasks_handler(
    tasks_repository: TasksRepository, relays_repository: RelaysRepository
) -> Iterator[GetRelayTasksHandler]:
    handler = GetRelayTasksHandler(
        tasks_repository=tasks_repository, relay_repository=relays_repository
    )
    yield handler


@pytest.fixture
def populated_repos(
    relays_repository: RelaysRepository,
    tasks_repository: TasksRepository,
    test_user: UserAuth,
) -> tuple[RelayID, RelayTask, RelaysRepository, TasksRepository]:
    # arrange
    # register a relay in the repository
    relay_id = relays_repository.add_relay(test_user, alias="test-relay")

    # insert a task in the repository
    now = datetime.now(UTC)
    spec = FetchSpec(
        timeout=60,
        payload='{"url": "http://example.com/data"}',
    )
    task = RelayTask(
        id=TaskID("test-task-id"),
        spec=spec,
        creation_timestamp=now,
        update_timestamp=now,
    )
    tasks_repository.store_task(relay_id=relay_id, task=task)

    return relay_id, task, relays_repository, tasks_repository
