#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Request-layer tests for the map router endpoints (``api/v1/maps``).

The daemon owns ``register`` and the background upload/delete; map CRUD and
legacy .cfg parsing live GUI-side (the visuals store and
``cmk.maps.gui._cfg_import``).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import override

import pytest
from conftest import RouterClientFactory
from fake_connection import FakeConnection
from fastapi.testclient import TestClient

from cmk.maps.backend.api.v1 import deps, maps
from cmk.maps.backend.connections.base import GeoHost
from cmk.maps.backend.core.auth import Principal
from cmk.maps.backend.schemas.map import MapConfig, WorldmapView
from cmk.maps.backend.services import map_service, state_service

ADMIN_PRINCIPAL = Principal(name="admin", may_edit=True, configure=True, see_all=True)


@pytest.fixture
def client(router_client: RouterClientFactory) -> TestClient:
    return router_client(
        maps.router,
        "/api/v1/maps",
        overrides={deps.get_current_user: ADMIN_PRINCIPAL},
    )


def test_register_unsigned_own_returns_204(client: TestClient) -> None:
    # An unbound ticket (no map claim) may register an unsigned config for its
    # own namespace — the editor-preview path.
    resp = client.post(
        "/api/v1/maps/register",
        json={"config": {"name": "streamed", "alias": "Streamed"}},
    )
    assert resp.status_code == 204
    assert map_service.get_map(ADMIN_PRINCIPAL.name, "streamed") is not None


def test_register_unsigned_foreign_rejected(router_client: RouterClientFactory) -> None:
    # A ticket scoped to someone else's map may NOT push an unsigned config —
    # that path is own-map only, so a viewer can't poison a foreign shared loop.
    foreign = Principal(name="bob", map_owner="alice", map_name="shared")
    client = router_client(maps.router, "/api/v1/maps", overrides={deps.get_current_user: foreign})
    resp = client.post(
        "/api/v1/maps/register",
        json={"config": {"name": "shared", "alias": "Shared"}},
    )
    assert resp.status_code == 403
    assert map_service.get_map("alice", "shared") is None


def test_register_unsigned_without_edit_grant_rejected(
    router_client: RouterClientFactory,
) -> None:
    # The unsigned path is the editor preview, so it needs the edit grant. A
    # read-only user must not be able to hand the daemon a config to poll.
    viewer = Principal(name="carol", may_edit=False)
    client = router_client(maps.router, "/api/v1/maps", overrides={deps.get_current_user: viewer})
    resp = client.post(
        "/api/v1/maps/register",
        json={"config": {"name": "unowned", "alias": "Unowned"}},
    )
    assert resp.status_code == 403
    assert map_service.get_map("carol", "unowned") is None


def test_register_unsigned_name_mismatch_rejected(router_client: RouterClientFactory) -> None:
    # A map-scoped ticket may only register an unsigned preview for the map it
    # is bound to — a config carrying a different name is rejected, so a ticket for
    # one of the caller's maps can't register a preview under another name in their
    # own namespace (mirrors the signed path's name check).
    scoped = Principal(name="alice", map_owner="alice", map_name="mine")
    client = router_client(maps.router, "/api/v1/maps", overrides={deps.get_current_user: scoped})
    resp = client.post(
        "/api/v1/maps/register",
        json={"config": {"name": "other", "alias": "Other"}},
    )
    assert resp.status_code == 403
    assert map_service.get_map("alice", "other") is None


def test_register_missing_config_is_422(client: TestClient) -> None:
    resp = client.post("/api/v1/maps/register", json={})
    assert resp.status_code == 422


def test_register_signed_invalid_config_is_422_not_500(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
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
    resp = client.post(
        "/api/v1/maps/register", json={"config_b64": "irrelevant", "sig": "irrelevant"}
    )
    assert resp.status_code == 422


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
        scoped.map_key_owner,
        MapConfig(name="world", connection_id="spy", view=WorldmapView(auto_source="all_hosts")),
    )
    client = router_client(maps.router, "/api/v1/maps", overrides={deps.get_current_user: scoped})
    try:
        resp = client.get("/api/v1/maps/world/auto-objects")
        assert resp.status_code == 200
        assert spy.geo_query_auth_user == "bob"
    finally:
        state_service.unregister_connection("spy")
