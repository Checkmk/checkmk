#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Route-level behaviour of the read-only connection API.

Integration tests exercise ``/topology`` and ``/object-details`` against a live
site; these unit tests cover the router seams that integration doesn't isolate:
secret redaction on the connection list, the metric-history soft-failure
contract (unknown connection / backend error both degrade to an empty series
rather than a 5xx), and that every read query is wrapped in the caller's
Livestatus contact scope — unscoped only for see-all users.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager
from typing import override

import pytest
from conftest import RouterClientFactory
from fake_connection import FakeConnection

from cmk.maps.backend.api.v1 import connections, deps
from cmk.maps.backend.connections.base import MetricHistoryResult
from cmk.maps.backend.core.auth import Principal
from cmk.maps.backend.schemas.connection import ConnectionConfig, REDACTED_SECRET
from cmk.maps.backend.services import connection_service, state_service

pytestmark = pytest.mark.usefixtures("_clear_connections")

_ADMIN = Principal(name="cmkadmin", see_all=True, configure=True)
_SCOPED = Principal(name="bob", see_all=False)


@pytest.fixture
def _clear_connections() -> Iterator[None]:
    yield
    state_service._connections.clear()  # noqa: SLF001


class _ScopeSpyConnection(FakeConnection):
    """Records the auth-user each query was scoped to (empty = ran unscoped)."""

    def __init__(self) -> None:
        self.scoped_as: list[str] = []

    @asynccontextmanager
    @override
    async def with_auth_user(self, username: str) -> AsyncIterator[None]:
        self.scoped_as.append(username)
        yield


class _BrokenMetricConnection(FakeConnection):
    @override
    async def get_metric_history(
        self, host: str, service: str | None, start: int, end: int
    ) -> MetricHistoryResult:
        raise RuntimeError("rrd backend gone")


def test_list_backends_redacts_secrets(
    router_client: RouterClientFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    cfg = ConnectionConfig(
        id="c1",
        type="livestatus",
        label="C1",
        host="10.0.0.1",
        automation_user="automation",
        automation_secret="supersecret",
    )
    monkeypatch.setattr(connection_service, "load_all", lambda: [cfg])
    client = router_client(
        connections.router,
        "/api/v1/connections",
        overrides={deps.require_connection_read: _ADMIN},
    )

    resp = client.get("/api/v1/connections")

    assert resp.status_code == 200
    body = resp.json()
    assert body[0]["id"] == "c1"
    # The resolved secret must never leave the server on the read-only list API.
    assert body[0]["automation_secret"] == REDACTED_SECRET
    assert "supersecret" not in resp.text


def test_list_backends_hides_transport_without_configure(
    router_client: RouterClientFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The list is readable with the plain edit grant, which every ordinary role
    # has, so the endpoint details stay with maps.configure.
    cfg = ConnectionConfig(
        id="c1",
        type="livestatus",
        label="C1",
        host="10.0.0.1",
        port=6557,
        socket_path=None,
        automation_user="automation",
        automation_secret="supersecret",
        checkmk_url="/remote",
    )
    monkeypatch.setattr(connection_service, "load_all", lambda: [cfg])
    author = Principal(name="bob", may_edit=True)
    client = router_client(
        connections.router,
        "/api/v1/connections",
        overrides={deps.require_connection_read: author},
    )

    resp = client.get("/api/v1/connections")

    body = resp.json()
    assert body[0]["id"] == "c1"
    assert body[0]["label"] == "C1"
    assert body[0]["checkmk_url"] == "/remote"
    assert body[0]["host"] is None
    assert body[0]["port"] is None
    assert body[0]["socket_path"] is None
    assert body[0]["automation_user"] is None
    assert "supersecret" not in resp.text


def test_metric_history_returns_series(router_client: RouterClientFactory) -> None:
    state_service.register_connection("c1", FakeConnection())
    client = router_client(
        connections.router, "/api/v1/connections", overrides={deps.rate_limited_read: _ADMIN}
    )

    resp = client.get(
        "/api/v1/connections/c1/metric-history",
        params={"host": "localhost", "service": "CPU utilization", "minutes": 60},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["series"]  # synthetic series present
    assert body["error"] is None


def test_metric_history_unknown_connection_degrades_to_empty(
    router_client: RouterClientFactory,
) -> None:
    # An unregistered connection is a soft miss (empty series), not a 404 — the
    # client only needs "no data".
    client = router_client(
        connections.router, "/api/v1/connections", overrides={deps.rate_limited_read: _ADMIN}
    )

    resp = client.get("/api/v1/connections/absent/metric-history", params={"host": "localhost"})

    assert resp.status_code == 200
    assert resp.json()["series"] == {}


def test_metric_history_backend_error_is_soft_failure(
    router_client: RouterClientFactory,
) -> None:
    state_service.register_connection("c1", _BrokenMetricConnection())
    client = router_client(
        connections.router, "/api/v1/connections", overrides={deps.rate_limited_read: _ADMIN}
    )

    resp = client.get(
        "/api/v1/connections/c1/metric-history", params={"host": "localhost", "service": "PING"}
    )

    # A failing RRD fetch must not surface as a 5xx: empty series + an error flag.
    assert resp.status_code == 200
    body = resp.json()
    assert body["series"] == {}
    assert body["error"]


def test_metric_history_scopes_query_to_contact_user(
    router_client: RouterClientFactory,
) -> None:
    spy = _ScopeSpyConnection()
    state_service.register_connection("c1", spy)
    client = router_client(
        connections.router, "/api/v1/connections", overrides={deps.rate_limited_read: _SCOPED}
    )

    resp = client.get(
        "/api/v1/connections/c1/metric-history", params={"host": "localhost", "service": "PING"}
    )

    assert resp.status_code == 200
    # A contact-scoped user's read must be wrapped in their Livestatus AuthUser.
    assert spy.scoped_as == ["bob"]


def test_metric_history_see_all_user_runs_unscoped(
    router_client: RouterClientFactory,
) -> None:
    spy = _ScopeSpyConnection()
    state_service.register_connection("c1", spy)
    client = router_client(
        connections.router, "/api/v1/connections", overrides={deps.rate_limited_read: _ADMIN}
    )

    resp = client.get(
        "/api/v1/connections/c1/metric-history", params={"host": "localhost", "service": "PING"}
    )

    assert resp.status_code == 200
    # see-all bypasses AuthUser scoping — passing the raw name would filter cmkadmin
    # (typically no contact) down to zero rows.
    assert spy.scoped_as == []


def test_object_details_service_requires_service_param(
    router_client: RouterClientFactory,
) -> None:
    state_service.register_connection("c1", FakeConnection())
    client = router_client(
        connections.router, "/api/v1/connections", overrides={deps.rate_limited_read: _ADMIN}
    )

    resp = client.get(
        "/api/v1/connections/c1/object-details", params={"type": "service", "host": "localhost"}
    )

    assert resp.status_code == 400


def test_object_details_unknown_connection_returns_null(
    router_client: RouterClientFactory,
) -> None:
    client = router_client(
        connections.router, "/api/v1/connections", overrides={deps.rate_limited_read: _ADMIN}
    )

    resp = client.get(
        "/api/v1/connections/absent/object-details", params={"type": "host", "host": "h"}
    )

    assert resp.status_code == 200
    assert resp.json() is None
