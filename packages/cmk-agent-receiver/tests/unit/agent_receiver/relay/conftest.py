#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
from collections.abc import Iterator
from datetime import datetime, UTC
from http import HTTPStatus
from pathlib import Path

import httpx
import pytest
from pydantic import SecretStr

from cmk.agent_receiver.lib.config import Config
from cmk.agent_receiver.relay.api.routers.relays.handlers.register_relay import (
    GetRelayStatusHandler,
    RegisterRelayHandler,
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
from cmk.agent_receiver.relay.api.routers.tasks.libs.config_task_factory import ConfigTaskFactory
from cmk.agent_receiver.relay.api.routers.tasks.libs.tasks_repository import (
    FetchSpec,
    RelayTask,
    TasksRepository,
)
from cmk.agent_receiver.relay.lib.relays_repository import RelaysRepository
from cmk.agent_receiver.relay.lib.shared_types import RelayID, TaskID
from cmk.agent_receiver.relay.lib.site_auth import UserAuth
from cmk.testlib.agent_receiver.relay import random_relay_id


def create_relay_mock_transport() -> httpx.MockTransport:
    """Create a stateful mock transport for relay operations."""
    registered_relays: set[str] = set()

    def handler(request: httpx.Request) -> httpx.Response:
        # Create relay
        if request.method == "POST" and request.url.path.endswith(
            "/domain-types/relay/collections/all"
        ):
            request_data = json.loads(request.content)
            relay_id = request_data["relay_id"]
            registered_relays.add(relay_id)
            return httpx.Response(HTTPStatus.OK, json={"id": relay_id})

        # Check relay exists
        elif request.method == "GET" and "/objects/relay/" in request.url.path:
            relay_id = request.url.path.split("/")[-1]
            if relay_id in registered_relays:
                return httpx.Response(HTTPStatus.OK, json={"id": relay_id})
            return httpx.Response(HTTPStatus.NOT_FOUND, json={"error": "Relay not found"})

        # List relays
        elif request.method == "GET" and request.url.path.endswith(
            "/domain-types/relay/collections/all"
        ):
            items = [{"id": relay_id} for relay_id in registered_relays]
            return httpx.Response(HTTPStatus.OK, json={"value": items})

        # Unhandled request
        return httpx.Response(HTTPStatus.NOT_FOUND, json={"error": "Endpoint not found"})

    return httpx.MockTransport(handler)


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
def site_api_client() -> Iterator[httpx.Client]:
    """Provides an httpx.Client configured for the site API."""
    client = httpx.Client(
        base_url="http://test.com/test/check_mk/api/unstable",
        headers={"Content-Type": "application/json"},
        transport=create_relay_mock_transport(),
    )
    yield client
    client.close()


@pytest.fixture()
def relays_repository(
    site_api_client: httpx.Client, site_context: Config
) -> Iterator[RelaysRepository]:
    """Provides a RelaysRepository with mock transport for testing."""
    repository = RelaysRepository(
        site_api_client, siteid="test-site", helper_config_dir=site_context.helper_config_dir
    )
    yield repository


@pytest.fixture()
def tasks_repository() -> Iterator[TasksRepository]:
    """Provides a TasksRepository for testing."""
    repository = TasksRepository(ttl_seconds=10, max_pending_tasks_per_relay=5)
    yield repository


@pytest.fixture()
def register_relay_handler(relays_repository: RelaysRepository) -> Iterator[RegisterRelayHandler]:
    """Provides a RegisterRelayHandler with mock dependencies."""
    handler = RegisterRelayHandler(relays_repository=relays_repository)
    yield handler


@pytest.fixture()
def get_relay_status_handler(
    relays_repository: RelaysRepository,
) -> Iterator[GetRelayStatusHandler]:
    """Provides a GetRelayStatusHandler with mock dependencies."""
    handler = GetRelayStatusHandler(relays_repository=relays_repository)
    yield handler


@pytest.fixture()
def create_task_handler(tasks_repository: TasksRepository) -> Iterator[CreateTaskHandler]:
    """Provides a CreateTaskHandler with mock dependencies."""
    handler = CreateTaskHandler(tasks_repository=tasks_repository)
    yield handler


@pytest.fixture()
def update_task_handler(tasks_repository: TasksRepository) -> Iterator[UpdateTaskHandler]:
    """Provides an UpdateTaskHandler with mock dependencies."""
    handler = UpdateTaskHandler(tasks_repository=tasks_repository)
    yield handler


@pytest.fixture()
def get_task_handler(tasks_repository: TasksRepository) -> Iterator[GetRelayTaskHandler]:
    handler = GetRelayTaskHandler(tasks_repository=tasks_repository)
    yield handler


@pytest.fixture()
def get_tasks_handler(
    tasks_repository: TasksRepository,
    config_task_factory: ConfigTaskFactory,
) -> Iterator[GetRelayTasksHandler]:
    handler = GetRelayTasksHandler(
        tasks_repository=tasks_repository,
        config_task_factory=config_task_factory,
    )
    yield handler


@pytest.fixture()
def config_task_factory(
    tasks_repository: TasksRepository, relays_repository: RelaysRepository
) -> Iterator[ConfigTaskFactory]:
    yield ConfigTaskFactory(tasks_repository=tasks_repository, relays_repository=relays_repository)


@pytest.fixture
def populated_repos(
    relays_repository: RelaysRepository,
    tasks_repository: TasksRepository,
    test_user: UserAuth,
) -> tuple[RelayID, RelayTask, RelaysRepository, TasksRepository]:
    # arrange
    # register a relay in the repository
    relay_id = relays_repository.add_relay(
        test_user, relay_id=random_relay_id(), alias="test-relay"
    )

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
