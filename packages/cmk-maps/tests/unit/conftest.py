#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Shared fixtures for the Maps daemon unit tests."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterator
from typing import Protocol
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import APIRouter, FastAPI, Request
from fastapi.testclient import TestClient

from cmk.maps.backend.connections.base import ConnectionBase
from cmk.maps.backend.core.auth import Principal
from cmk.maps.backend.core.ratelimit import rest_read_limiter, ws_connect_limiter
from cmk.maps.backend.services import map_service, state_service

# A guard dependency is either ticket-authenticating off the request
# (``deps.get_current_user``) or chained onto the principal it resolved
# (``deps.rate_limited_read``, ``deps.require_connection_read``).
AuthDependency = (
    Callable[[Request], Awaitable[Principal]] | Callable[[Principal], Awaitable[Principal]]
)


class RouterClientFactory(Protocol):
    """Builds a ``TestClient`` for a single router with auth overrides."""

    def __call__(
        self,
        router: APIRouter,
        prefix: str,
        *,
        overrides: dict[AuthDependency, Principal] | None = None,
    ) -> TestClient: ...


@pytest.fixture
def router_client() -> Iterator[RouterClientFactory]:
    """Mount one router on a fresh ``FastAPI`` app and return a ``TestClient``.

    This skips the daemon's heavy module-level ``lifespan`` (which requires a
    real Livestatus connection) and isolates the router under test. Pass
    ``overrides`` mapping each guard dependency (e.g. ``deps.get_current_user``)
    to the :class:`Principal` it should resolve to, so the per-route auth can be
    set to admin / scoped / view-only without minting real tickets.
    """
    clients: list[TestClient] = []

    def _build(
        router: APIRouter,
        prefix: str,
        *,
        overrides: dict[AuthDependency, Principal] | None = None,
    ) -> TestClient:
        app = FastAPI()
        app.include_router(router, prefix=prefix)
        for dependency, principal in (overrides or {}).items():
            app.dependency_overrides[dependency] = lambda principal=principal: principal
        client = TestClient(app, raise_server_exceptions=True)
        clients.append(client)
        return client

    yield _build

    for client in clients:
        client.close()


@pytest.fixture(autouse=True)  # ruff: ignore[pytest-fixture-autouse]
def _clear_map_caches() -> Iterator[None]:
    """Drop the in-memory map cache and state-snapshot dicts after each test so
    a map registered by one route test cannot bleed into the next."""
    yield
    map_service._CACHE.clear()  # noqa: SLF001
    state_service._state_snapshots.clear()  # noqa: SLF001
    state_service._timing_snapshots.clear()  # noqa: SLF001
    state_service._folder_tree_snapshots.clear()  # noqa: SLF001
    state_service._topology_snapshots.clear()  # noqa: SLF001
    state_service._topology_timing_snapshots.clear()  # noqa: SLF001
    # Module-level rate-limiter singletons: reset so one test's request count
    # can't push another over the per-user/-IP budget.
    rest_read_limiter._calls.clear()  # noqa: SLF001
    ws_connect_limiter._calls.clear()  # noqa: SLF001


@pytest.fixture
def mock_connection() -> MagicMock:
    """A fully stubbed ``ConnectionBase`` with every async method defaulted.

    Every coroutine method on the abstract base is pre-stubbed as an
    ``AsyncMock`` with an empty/neutral default so any test can register the
    connection and override just the methods it cares about. ``spec`` keeps the
    mock honest: a typo on a non-existent method raises instead of silently
    returning a new mock.
    """
    connection = MagicMock(spec=ConnectionBase)
    connection.connection_id = "mock_connection"
    connection.is_available = AsyncMock(return_value=True)

    connection.get_host_state = AsyncMock()
    connection.get_service_state = AsyncMock()
    connection.get_host_hard_state = AsyncMock()
    connection.get_service_hard_state = AsyncMock()
    connection.get_hostgroup_states = AsyncMock()
    connection.get_servicegroup_states = AsyncMock()

    connection.get_hosts_states = AsyncMock(return_value={})
    connection.get_services_states = AsyncMock(return_value={})
    connection.get_all_hosts_states = AsyncMock(return_value={})
    connection.get_all_services_states = AsyncMock(return_value={})
    connection.get_hosts_services_batch = AsyncMock(return_value={})
    connection.get_host_services = AsyncMock(return_value=[])
    connection.get_services_summary = AsyncMock(return_value={})

    connection.get_group_members = AsyncMock(return_value=[])

    connection.get_dyngroup_state = AsyncMock(
        return_value=None,
    )

    connection.get_hosts_with_geo = AsyncMock(return_value=[])

    connection.get_folder_tree = AsyncMock()
    connection.search_services = AsyncMock(return_value=[])

    connection.get_host_details = AsyncMock(return_value=None)
    connection.get_service_details = AsyncMock(return_value=None)

    connection.get_topology = AsyncMock(return_value=[])

    connection.get_metric_history = AsyncMock()

    return connection
