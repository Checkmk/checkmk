#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Request-layer tests for the map router endpoints (``api/v1/maps``).

The daemon owns ``register`` and the background upload/delete; map CRUD and
legacy .cfg parsing live GUI-side (the visuals store and
``cmk.maps.gui._cfg_import``).
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from http import HTTPStatus
from typing import override

import pytest
from fake_connection import FakeConnection
from fastapi.testclient import TestClient
from router_client import RouterClientFactory

from cmk.maps.backend.api.v1 import deps, maps
from cmk.maps.backend.connections.base import GeoHost
from cmk.maps.backend.core.auth import Principal
from cmk.maps.backend.schemas.map import MapConfig, WorldmapView
from cmk.maps.backend.services import map_service, state_service

ADMIN_PRINCIPAL = Principal(name="admin", may_edit=True, configure=True, see_all=True)


def _client(
    router_client: RouterClientFactory, user: Principal, *, owner: str | None
) -> TestClient:
    """A client for ``user``, to whom the GUI names ``owner`` for every map name."""
    return router_client(
        maps.router,
        "/api/v1/maps",
        overrides={deps.get_current_user: user, deps.get_map_owner: owner},
    )


def test_register_unsigned_own_map_returns_204(router_client: RouterClientFactory) -> None:
    client = _client(router_client, ADMIN_PRINCIPAL, owner=ADMIN_PRINCIPAL.name)
    resp = client.post(
        "/api/v1/maps/streamed/register",
        json={"config": {"name": "streamed", "alias": "Streamed"}},
    )
    assert resp.status_code == HTTPStatus.NO_CONTENT
    assert map_service.get_map(ADMIN_PRINCIPAL.name, "streamed") is not None


def test_register_unsigned_for_a_map_the_user_does_not_see_is_404(
    router_client: RouterClientFactory,
) -> None:
    client = _client(router_client, ADMIN_PRINCIPAL, owner=None)
    resp = client.post(
        "/api/v1/maps/gone/register",
        json={"config": {"name": "gone", "alias": "Gone"}},
    )
    assert resp.status_code == HTTPStatus.NOT_FOUND
    assert map_service.get_map(ADMIN_PRINCIPAL.name, "gone") is None


def test_register_unsigned_foreign_rejected(router_client: RouterClientFactory) -> None:
    client = _client(router_client, Principal(name="bob", may_edit=True), owner="alice")
    resp = client.post(
        "/api/v1/maps/shared/register",
        json={"config": {"name": "shared", "alias": "Shared"}},
    )
    assert resp.status_code == HTTPStatus.FORBIDDEN
    assert map_service.get_map("alice", "shared") is None
    assert map_service.get_map("bob", "shared") is None


def test_register_unsigned_without_edit_grant_rejected(
    router_client: RouterClientFactory,
) -> None:
    # The unsigned path is the editor preview, so it needs the edit grant. A
    # read-only user must not be able to hand the daemon a config to poll.
    client = _client(router_client, Principal(name="carol", may_edit=False), owner="carol")
    resp = client.post(
        "/api/v1/maps/unowned/register",
        json={"config": {"name": "unowned", "alias": "Unowned"}},
    )
    assert resp.status_code == HTTPStatus.FORBIDDEN
    assert map_service.get_map("carol", "unowned") is None


def test_register_unsigned_name_mismatch_rejected(router_client: RouterClientFactory) -> None:
    client = _client(router_client, Principal(name="alice", may_edit=True), owner="alice")
    resp = client.post(
        "/api/v1/maps/mine/register",
        json={"config": {"name": "other", "alias": "Other"}},
    )
    assert resp.status_code == HTTPStatus.FORBIDDEN
    assert map_service.get_map("alice", "other") is None


def test_register_missing_config_is_422(router_client: RouterClientFactory) -> None:
    client = _client(router_client, ADMIN_PRINCIPAL, owner=None)
    resp = client.post("/api/v1/maps/streamed/register", json={})
    assert resp.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


def test_register_signed_for_a_map_the_user_does_not_see_is_404(
    router_client: RouterClientFactory,
) -> None:
    client = _client(router_client, ADMIN_PRINCIPAL, owner=None)
    resp = client.post(
        "/api/v1/maps/secret/register", json={"config_b64": "irrelevant", "sig": "irrelevant"}
    )
    assert resp.status_code == HTTPStatus.NOT_FOUND


def test_register_signed_invalid_config_is_422_not_500(
    router_client: RouterClientFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    # The GUI store can persist a value this schema rejects (e.g. an object_filter
    # without a ``Filter:`` header). When that map is later signed and registered,
    # the manual model_validate must surface a 422 rather than crashing into the
    # daemon's generic 500 handler and writing a crash report on every load.
    monkeypatch.setattr(
        maps,
        "verify_map_config",
        lambda *_args, **_kwargs: {
            "name": "streamed",
            "alias": "Streamed",
            "objects": [{"id": "dg", "type": "dyngroup", "object_filter": "host_name ~ srv"}],
        },
    )
    client = _client(router_client, ADMIN_PRINCIPAL, owner="admin")
    resp = client.post(
        "/api/v1/maps/streamed/register", json={"config_b64": "irrelevant", "sig": "irrelevant"}
    )
    assert resp.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


class _AuthScopeSpyConnection(FakeConnection):
    """Records the auth_user active when the geo-host query runs."""

    connection_id = "spy"

    def __init__(self) -> None:
        self.geo_query_auth_user: str | None = "NOT_CALLED"
        self._active_auth_user: str | None = None

    @asynccontextmanager
    @override
    async def with_auth_user(self, username: str) -> AsyncIterator[None]:
        self._active_auth_user = username
        try:
            yield
        finally:
            self._active_auth_user = None

    @override
    async def get_hosts_with_geo(
        self, *, group_type: str | None = None, group_name: str | None = None
    ) -> list[GeoHost]:
        self.geo_query_auth_user = self._active_auth_user
        return []


def test_auto_objects_scopes_geo_query_to_auth_user(
    router_client: RouterClientFactory,
) -> None:
    # A non-see-all user must not enumerate every geo host in the site: the
    # underlying Livestatus query has to run inside their AuthUser scope, not
    # unscoped.
    spy = _AuthScopeSpyConnection()
    state_service.register_connection("spy", spy)
    scoped = Principal(name="bob", may_edit=True, see_all=False)  # auth_user == "bob"
    map_service.register_map(
        "bob",
        MapConfig(name="world", connection_id="spy", view=WorldmapView(auto_source="all_hosts")),
    )
    client = _client(router_client, scoped, owner="bob")
    try:
        resp = client.get("/api/v1/maps/world/auto-objects")
        assert resp.status_code == HTTPStatus.OK
        assert spy.geo_query_auth_user == "bob"
    finally:
        state_service.unregister_connection("spy")


def test_auto_objects_is_404_for_a_map_the_user_does_not_see(
    router_client: RouterClientFactory,
) -> None:
    map_service.register_map(
        "alice",
        MapConfig(name="world", connection_id="live_1", view=WorldmapView(auto_source="all_hosts")),
    )
    client = _client(router_client, Principal(name="bob"), owner=None)

    resp = client.get("/api/v1/maps/world/auto-objects")

    assert resp.status_code == HTTPStatus.NOT_FOUND
