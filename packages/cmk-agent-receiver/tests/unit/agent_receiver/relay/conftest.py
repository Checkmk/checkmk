#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
from collections.abc import AsyncIterator, Iterator
from datetime import datetime, UTC
from http import HTTPStatus

import httpx2
import pytest
import pytest_asyncio
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
from cmk.agent_receiver.relay.lib.relay_config_repository import RelayConfigRepository
from cmk.agent_receiver.relay.lib.shared_types import RelayID, TaskID
from cmk.agent_receiver.relay.lib.site_auth import SecretAuth
from cmk.agent_receiver.relay.lib.site_client import SiteRelaysClient
from cmk.testlib.agent_receiver.relay import random_relay_id


def create_relay_mock_transport() -> httpx2.MockTransport:
    """Create a stateful mock transport for relay operations."""
    registered_relays: set[str] = set()

    def handler(request: httpx2.Request) -> httpx2.Response:
        # Create relay
        if request.method == "POST" and request.url.path.endswith(
            "/domain-types/relay/collections/all"
        ):
            request_data = json.loads(request.content)
            relay_id = request_data["relay_id"]
            registered_relays.add(relay_id)
            return httpx2.Response(HTTPStatus.OK, json={"id": relay_id})

        # Check relay exists
        if request.method == "GET" and "/objects/relay/" in request.url.path:
            relay_id = request.url.path.split("/")[-1]
            if relay_id in registered_relays:
                return httpx2.Response(HTTPStatus.OK, json={"id": relay_id})
            return httpx2.Response(HTTPStatus.NOT_FOUND, json={"error": "Relay not found"})

        # List relays
        if request.method == "GET" and request.url.path.endswith(
            "/domain-types/relay/collections/all"
        ):
            items = [{"id": relay_id} for relay_id in registered_relays]
            return httpx2.Response(HTTPStatus.OK, json={"value": items})

        # Unhandled request
        return httpx2.Response(HTTPStatus.NOT_FOUND, json={"error": "Endpoint not found"})

    return httpx2.MockTransport(handler)


@pytest.fixture
def site_context(setup_site_context: Config) -> Config:
    setup_site_context.internal_secret_path.parent.mkdir(parents=True, exist_ok=True)
    setup_site_context.internal_secret_path.write_text("lol")
    return setup_site_context


@pytest.fixture()
def test_user() -> SecretAuth:
    return SecretAuth(SecretStr("Bearer test-token"))


@pytest.fixture()
def _relay_mock_transport() -> httpx2.MockTransport:
    """Shared mock transport so both clients see the same relay state."""
    return create_relay_mock_transport()


@pytest_asyncio.fixture()
async def site_api_client(
    _relay_mock_transport: httpx2.MockTransport,
) -> AsyncIterator[httpx2.AsyncClient]:
    """Provides an httpx2.AsyncClient configured for the site API (v1)."""
    async with httpx2.AsyncClient(
        base_url="http://test.com/test/check_mk/api/1.0",
        headers={"Content-Type": "application/json"},
        transport=_relay_mock_transport,
    ) as client:
        yield client


@pytest_asyncio.fixture()
async def internal_api_client(
    _relay_mock_transport: httpx2.MockTransport,
) -> AsyncIterator[httpx2.AsyncClient]:
    """Provides an httpx2.AsyncClient configured for the internal API."""
    async with httpx2.AsyncClient(
        base_url="http://test.com/test/check_mk/api/internal",
        headers={"Content-Type": "application/json"},
        transport=_relay_mock_transport,
    ) as client:
        yield client


@pytest.fixture()
def site_relays_client(
    site_api_client: httpx2.AsyncClient, internal_api_client: httpx2.AsyncClient
) -> Iterator[SiteRelaysClient]:
    """Provides a SiteRelaysClient with mock transport for testing."""
    repository = SiteRelaysClient(
        client=site_api_client,
        internal_client=internal_api_client,
        siteid="test-site",
    )
    yield repository


@pytest.fixture()
def tasks_repository() -> Iterator[TasksRepository]:
    """Provides a TasksRepository for testing."""
    repository = TasksRepository(ttl_seconds=10, max_pending_tasks_per_relay=5)
    yield repository


@pytest.fixture()
def register_relay_handler(site_relays_client: SiteRelaysClient) -> Iterator[RegisterRelayHandler]:
    """Provides a RegisterRelayHandler with mock dependencies."""
    handler = RegisterRelayHandler(site_relays_client=site_relays_client)
    yield handler


@pytest.fixture()
def get_relay_status_handler(
    site_relays_client: SiteRelaysClient, site_context: Config
) -> Iterator[GetRelayStatusHandler]:
    """Provides a GetRelayStatusHandler with mock dependencies."""
    handler = GetRelayStatusHandler(
        site_relays_client=site_relays_client,
        relay_config_repository=RelayConfigRepository(
            helper_config_dir=site_context.helper_config_dir
        ),
    )
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
    tasks_repository: TasksRepository, site_context: Config
) -> Iterator[ConfigTaskFactory]:
    yield ConfigTaskFactory(
        tasks_repository=tasks_repository,
        relay_config_repository=RelayConfigRepository(
            helper_config_dir=site_context.helper_config_dir
        ),
    )


@pytest.fixture
def populated_repos(
    tasks_repository: TasksRepository,
) -> tuple[RelayID, RelayTask, TasksRepository]:
    relay_id = random_relay_id()

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

    return relay_id, task, tasks_repository
