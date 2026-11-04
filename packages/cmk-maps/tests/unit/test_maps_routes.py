#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Request-layer tests for the map router endpoints (``api/v1/maps``).

The daemon owns ``register`` and the background upload/delete; map CRUD and
legacy .cfg parsing live GUI-side (the visuals store and
``cmk.maps.gui._cfg_import``).
"""

import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from http import HTTPStatus
from pathlib import Path
from typing import override

import httpx2
import pytest
from fake_connection import FakeConnection
from fake_links import FakeLinkGui
from fastapi import FastAPI
from fastapi.testclient import TestClient
from router_client import AuthDependency, RouterClientFactory

from cmk.crypto.secrets import Secret
from cmk.maps.backend.api.v1 import deps, maps, states
from cmk.maps.backend.connections.base import GeoHost
from cmk.maps.backend.core.auth import Principal
from cmk.maps.backend.core.ratelimit import rest_read_limiter
from cmk.maps.backend.core.sse import manager, Subscriber
from cmk.maps.backend.schemas.map import MapConfig, RadarView, WorldmapView
from cmk.maps.backend.schemas.state import ObjectState
from cmk.maps.backend.services import map_service, state_service
from cmk.maps.shared.map_signature import sign_config

ADMIN_PRINCIPAL = Principal(name="admin", may_edit=True, configure=True, see_all=True)


def _client(
    router_client: RouterClientFactory, user: Principal, *, owner: str | None
) -> TestClient:
    """A client for ``user``, to whom the GUI names ``owner`` for every map name."""
    return router_client(
        maps.router,
        "/api/v1/maps",
        overrides={
            deps.get_current_user: user,
            deps.get_map_owner: owner,
            deps.get_gui_auth: FakeLinkGui(),
        },
    )


def test_register_unsigned_own_is_cached(router_client: RouterClientFactory) -> None:
    client = _client(router_client, ADMIN_PRINCIPAL, owner=ADMIN_PRINCIPAL.name)
    resp = client.post(
        "/api/v1/maps/streamed/register",
        json={"config": {"name": "streamed", "alias": "Streamed"}},
    )
    assert resp.status_code == HTTPStatus.OK
    assert map_service.get_map(ADMIN_PRINCIPAL.name, "streamed") is not None


def test_register_with_the_read_budget_spent_still_caches_the_map(
    router_client: RouterClientFactory,
) -> None:
    client = _client(router_client, ADMIN_PRINCIPAL, owner=ADMIN_PRINCIPAL.name)
    for _ in range(rest_read_limiter._max):  # noqa: SLF001
        rest_read_limiter.record(ADMIN_PRINCIPAL.name)
    resp = client.post(
        "/api/v1/maps/streamed/register",
        json={"config": {"name": "streamed", "alias": "Streamed"}},
    )
    assert resp.status_code == HTTPStatus.TOO_MANY_REQUESTS
    assert map_service.get_map(ADMIN_PRINCIPAL.name, "streamed") is not None


def test_register_answers_with_the_states_the_caller_may_see(
    router_client: RouterClientFactory,
) -> None:
    client = _client(router_client, Principal(name="bob", may_edit=True), owner="bob")
    spy = _AuthScopeSpyConnection()
    state_service.register_connection("spy", spy)
    try:
        resp = client.post(
            "/api/v1/maps/mine/register",
            json={
                "config": {
                    "name": "mine",
                    "alias": "Mine",
                    "connection_id": "spy",
                    "objects": [{"id": "host:h1", "type": "host", "host_name": "localhost"}],
                }
            },
        )
    finally:
        state_service.unregister_connection("spy")

    assert resp.status_code == HTTPStatus.OK
    assert [state["object_id"] for state in resp.json()["states"]] == ["host:h1"]
    assert spy.hosts_query_auth_user == "bob"


def test_register_keeps_the_saved_view_of_a_previewed_map(
    router_client: RouterClientFactory,
) -> None:
    client = _client(router_client, ADMIN_PRINCIPAL, owner=ADMIN_PRINCIPAL.name)
    resp = client.post(
        "/api/v1/maps/radar/register",
        params={"radar_filter": "all_hosts", "radar_filter_value": ""},
        json={
            "config": {
                "name": "radar",
                "alias": "Radar",
                "view": {"type": "radar", "filter": "hostgroup", "filter_value": "web"},
            }
        },
    )

    assert resp.status_code == HTTPStatus.OK
    cached = map_service.get_map(ADMIN_PRINCIPAL.name, "radar")
    assert cached is not None
    assert isinstance(cached.view, RadarView)
    assert cached.view.filter == "hostgroup"


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


_SECRET = Secret(b"0123456789abcdef0123456789abcdef")


def _register_signed(client: TestClient, alias: str, *, saved: bool = True) -> None:
    signed = sign_config({"name": "streamed", "alias": alias}, _SECRET.hmac, owner="admin")
    resp = client.post("/api/v1/maps/streamed/register", json={**signed, "saved": saved})
    assert resp.status_code == HTTPStatus.OK


def _saved_events(sub: Subscriber) -> list[dict[str, str]]:
    events = []
    while not sub.queue.empty():
        event = sub.queue.get_nowait()
        if event.event == "map_saved":
            events.append(json.loads(event.raw_data or ""))
    return events


def test_open_views_hear_which_version_an_editor_registers(
    router_client: RouterClientFactory, site_secret_file: Path
) -> None:
    site_secret_file.write_bytes(_SECRET.reveal())
    client = _client(router_client, ADMIN_PRINCIPAL, owner="admin")
    sub = manager.subscribe("admin\x00streamed", None)
    try:
        _register_signed(client, "v2")
    finally:
        manager.unsubscribe("admin\x00streamed", sub)

    signed = sign_config({"name": "streamed", "alias": "v2"}, _SECRET.hmac, owner="admin")
    assert _saved_events(sub) == [{"type": "map_saved", "map": "streamed", "sig": signed["sig"]}]


def test_a_save_registered_without_states_tells_the_open_views_and_answers_none(
    router_client: RouterClientFactory, site_secret_file: Path
) -> None:
    site_secret_file.write_bytes(_SECRET.reveal())
    client = _client(router_client, ADMIN_PRINCIPAL, owner="admin")
    signed = sign_config({"name": "streamed", "alias": "v2"}, _SECRET.hmac, owner="admin")
    sub = manager.subscribe("admin\x00streamed", None)
    try:
        resp = client.post("/api/v1/maps/streamed/saved", json=signed)
    finally:
        manager.unsubscribe("admin\x00streamed", sub)

    assert (resp.status_code, resp.content) == (HTTPStatus.NO_CONTENT, b"")
    assert _saved_events(sub) == [{"type": "map_saved", "map": "streamed", "sig": signed["sig"]}]


def test_opening_a_map_tells_no_view(
    router_client: RouterClientFactory, site_secret_file: Path
) -> None:
    site_secret_file.write_bytes(_SECRET.reveal())
    client = _client(router_client, ADMIN_PRINCIPAL, owner="admin")
    sub = manager.subscribe("admin\x00streamed", None)
    try:
        _register_signed(client, "v2", saved=False)
    finally:
        manager.unsubscribe("admin\x00streamed", sub)

    assert _saved_events(sub) == []


def test_an_editor_past_the_read_budget_tells_no_view(
    router_client: RouterClientFactory, site_secret_file: Path
) -> None:
    site_secret_file.write_bytes(_SECRET.reveal())
    client = _client(router_client, ADMIN_PRINCIPAL, owner="admin")
    for _ in range(rest_read_limiter._max):  # noqa: SLF001
        rest_read_limiter.record(ADMIN_PRINCIPAL.name)
    sub = manager.subscribe("admin\x00streamed", None)
    try:
        signed = sign_config({"name": "streamed", "alias": "v2"}, _SECRET.hmac, owner="admin")
        client.post("/api/v1/maps/streamed/register", json={**signed, "saved": True})
    finally:
        manager.unsubscribe("admin\x00streamed", sub)

    assert _saved_events(sub) == []


@pytest.mark.parametrize(
    "viewer",
    [
        pytest.param(Principal(name="viewer", see_all=True), id="read-only"),
        pytest.param(Principal(name="viewer", may_edit=True, see_all=True), id="editing own maps"),
    ],
)
def test_a_viewer_registering_another_version_tells_no_view(
    router_client: RouterClientFactory, site_secret_file: Path, viewer: Principal
) -> None:
    site_secret_file.write_bytes(_SECRET.reveal())
    client = _client(router_client, viewer, owner="admin")
    sub = manager.subscribe("admin\x00streamed", None)
    try:
        _register_signed(client, "v1")
        _register_signed(client, "v2")
    finally:
        manager.unsubscribe("admin\x00streamed", sub)

    assert _saved_events(sub) == []


def test_open_views_hear_which_version_an_admin_saved_of_another_users_map(
    router_client: RouterClientFactory, site_secret_file: Path
) -> None:
    site_secret_file.write_bytes(_SECRET.reveal())
    other_admin = Principal(name="root", may_edit=True, may_edit_foreign=True, see_all=True)
    client = _client(router_client, other_admin, owner="admin")
    sub = manager.subscribe("admin\x00streamed", None)
    try:
        _register_signed(client, "v2")
    finally:
        manager.unsubscribe("admin\x00streamed", sub)

    signed = sign_config({"name": "streamed", "alias": "v2"}, _SECRET.hmac, owner="admin")
    assert _saved_events(sub) == [{"type": "map_saved", "map": "streamed", "sig": signed["sig"]}]


class _AuthScopeSpyConnection(FakeConnection):
    """Records the auth_user active when the geo-host and host-state queries run."""

    connection_id = "spy"

    def __init__(self) -> None:
        self.geo_query_auth_user: str | None = "NOT_CALLED"
        self.hosts_query_auth_user: str | None = "NOT_CALLED"
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

    @override
    async def get_hosts_states(
        self, hostnames: list[str], only_hard: bool = False
    ) -> dict[str, ObjectState]:
        self.hosts_query_auth_user = self._active_auth_user
        return await super().get_hosts_states(hostnames, only_hard)


class _CountingConnection(FakeConnection):
    connection_id = "counting"

    def __init__(self) -> None:
        self.host_queries = 0

    @override
    async def get_hosts_states(
        self, hostnames: list[str], only_hard: bool = False
    ) -> dict[str, ObjectState]:
        self.host_queries += 1
        return await super().get_hosts_states(hostnames, only_hard)


def test_a_poll_after_the_map_was_registered_anew_asks_livestatus_again(
    router_client: RouterClientFactory,
) -> None:
    counting = _CountingConnection()
    state_service.register_connection("counting", counting)
    overrides: dict[AuthDependency, object] = {
        deps.get_current_user: ADMIN_PRINCIPAL,
        deps.get_map_owner: ADMIN_PRINCIPAL.name,
        deps.get_gui_auth: FakeLinkGui(),
    }
    maps_client = router_client(maps.router, "/api/v1/maps", overrides=overrides)
    states_client = router_client(states.router, "/api/v1", overrides=overrides)
    config = {
        "name": "polled",
        "connection_id": "counting",
        "objects": [{"id": "host:h1", "type": "host", "host_name": "localhost"}],
    }
    try:
        for alias in ("v1", "v2"):
            registered = maps_client.post(
                "/api/v1/maps/polled/register", json={"config": {**config, "alias": alias}}
            )
            assert registered.status_code == HTTPStatus.OK
            assert states_client.get("/api/v1/maps/polled/states").status_code == HTTPStatus.OK
    finally:
        state_service.unregister_connection("counting")

    # Each register answers with states of its own, and each first poll after it.
    assert counting.host_queries == 4


class _HeldConnection(FakeConnection):
    connection_id = "held"

    def __init__(self) -> None:
        self.hold_next = False
        self.held = asyncio.Event()
        self.release = asyncio.Event()

    @override
    async def get_hosts_states(
        self, hostnames: list[str], only_hard: bool = False
    ) -> dict[str, ObjectState]:
        if self.hold_next:
            self.hold_next = False
            self.held.set()
            await self.release.wait()
        return await super().get_hosts_states(hostnames, only_hard)


def test_a_poll_after_the_map_was_registered_shows_it_although_an_older_poll_ended_later() -> None:
    held = _HeldConnection()
    gui = FakeLinkGui()
    state_service.register_connection("held", held)
    app = FastAPI()
    app.include_router(maps.router, prefix="/api/v1/maps")
    app.include_router(states.router, prefix="/api/v1")
    app.dependency_overrides.update(
        {
            deps.get_current_user: lambda: ADMIN_PRINCIPAL,
            deps.get_map_owner: lambda: ADMIN_PRINCIPAL.name,
            deps.get_gui_auth: lambda: gui,
        }
    )

    def _config(host_object: str) -> dict[str, object]:
        return {
            "name": "polled",
            "connection_id": "held",
            "objects": [{"id": host_object, "type": "host", "host_name": "localhost"}],
        }

    async def _poll_across_a_register() -> list[str]:
        async with httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=app), base_url="http://test"
        ) as client:
            registered = await client.post(
                "/api/v1/maps/polled/register", json={"config": _config("host:old")}
            )
            assert registered.status_code == HTTPStatus.OK
            held.hold_next = True
            older = asyncio.ensure_future(client.get("/api/v1/maps/polled/states"))
            await held.held.wait()
            await client.post("/api/v1/maps/polled/register", json={"config": _config("host:new")})
            held.release.set()
            await older
            later = await client.get("/api/v1/maps/polled/states")
            return [state["object_id"] for state in later.json()["states"]]

    try:
        assert asyncio.run(_poll_across_a_register()) == ["host:new"]
    finally:
        state_service.unregister_connection("held")


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


def test_auto_objects_counts_against_the_read_budget(
    router_client: RouterClientFactory,
) -> None:
    map_service.register_map(
        "bob",
        MapConfig(name="world", connection_id="live_1", view=WorldmapView(auto_source="all_hosts")),
    )
    client = _client(router_client, Principal(name="bob"), owner="bob")
    for _ in range(rest_read_limiter._max):  # noqa: SLF001
        rest_read_limiter.record("bob")

    resp = client.get("/api/v1/maps/world/auto-objects")

    assert resp.status_code == HTTPStatus.TOO_MANY_REQUESTS


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
