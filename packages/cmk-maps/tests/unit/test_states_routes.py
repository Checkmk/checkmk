#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""SSE streaming layer of the states router.

The per-(map, auth_user) *delta* computation is covered by
``test_state_service_resolution.py``; what was untested is the layer that drives
it: the shared broadcast loop, its error resilience, the map-key isolation, and
the session checks of the SSE endpoint. Those are the parts that
run unattended and, if they regress, silently freeze or cross-wire live maps.

Async coroutines are driven with ``asyncio.run`` (no asyncio plugin in this
target); the loop is bounded by unsubscribing the sole subscriber from a patched
``asyncio.sleep`` so it exits deterministically instead of running forever.
"""

import asyncio
import json
from collections.abc import Awaitable, Callable, Iterator
from http import HTTPStatus
from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx2
import pytest
from fake_connection import FakeConnection
from fake_links import FakeLinkGui
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from starlette.types import Message

from cmk.fastapi.gui_session import GuiLoopback
from cmk.fastapi.sse import SentEvent
from cmk.maps.backend.api.v1 import deps, states
from cmk.maps.backend.app import create_app
from cmk.maps.backend.core.auth import GuiAuth, Principal
from cmk.maps.backend.core.middleware import CompactGZipMiddleware
from cmk.maps.backend.core.ratelimit import (
    kept_states_limiter,
    RateLimiter,
    rest_read_limiter,
    sse_stream_limiter,
    ws_connect_limiter,
)
from cmk.maps.backend.core.sse import manager, Subscriber
from cmk.maps.backend.integrations.checkmk import FolderScope
from cmk.maps.backend.schemas.map import FlowView, MapConfig, RadarView
from cmk.maps.backend.schemas.state import MapStates, ObjectState, ObjectTiming
from cmk.maps.backend.schemas.stream import StreamMessage
from cmk.maps.backend.services import map_service, settings_service, state_service
from cmk.maps.backend.services.settings_service import get_daemon_runtime

pytestmark = pytest.mark.usefixtures("_clear_stream_state")

_SITE = "heute"
_PERMISSIONS = {
    "maps.use": True,
    "general.edit_map": False,
    "general.edit_foreign_map": False,
    "maps.configure": False,
    "general.see_all": False,
    "wato.see_all_folders": False,
}


class _GUI:
    """A GUI to which the session cookie is the user's name, and every map is alice's.

    A session can be logged out, and a map unpublished, while a stream is open.
    """

    def __init__(self) -> None:
        self.logged_out: set[str] = set()
        self.unpublished: set[str] = set()
        self.down = False

    def handle(self, request: httpx2.Request) -> httpx2.Response:
        if self.down:
            return httpx2.Response(HTTPStatus.SERVICE_UNAVAILABLE)
        body = json.loads(request.content)
        if request.url.path.endswith("/identify/invoke"):
            if body["session_cookie"] in {"forged", *self.logged_out}:
                return httpx2.Response(
                    HTTPStatus.BAD_REQUEST,
                    json={"title": "t", "status": 400, "ext": {"error": "invalid_grant"}},
                )
            return httpx2.Response(
                HTTPStatus.OK,
                json={
                    "user_id": body["session_cookie"],
                    "permissions": _PERMISSIONS,
                    "contact_groups": [],
                },
            )
        if body["name"] in self.unpublished:
            return httpx2.Response(HTTPStatus.OK, json={})
        return httpx2.Response(HTTPStatus.OK, json={"owner": "alice"})

    def auth(self) -> GuiAuth:
        return GuiAuth(
            GuiLoopback(
                httpx2.AsyncClient(
                    base_url="http://gui", transport=httpx2.MockTransport(self.handle)
                )
            )
        )


def _session(user: str) -> dict[str, str]:
    return {"Cookie": f"auth_{_SITE}={user}"}


@pytest.fixture
def _clear_stream_state() -> Iterator[None]:
    """The shared conftest clears map/snapshot state; also drop SSE subscribers
    and per-map broadcast bookkeeping so streams don't bleed across tests."""
    yield
    manager._subscribers.clear()  # noqa: SLF001
    manager._closed = False  # noqa: SLF001
    states._broadcast_tasks.clear()  # noqa: SLF001
    states._dead_sites_snapshots.clear()  # noqa: SLF001


# --------------------------------------------------------------------------- #
# Pure helpers
# --------------------------------------------------------------------------- #


def test_map_key_isolates_owner_and_name() -> None:
    # Two users' same-named maps must never share a broadcast loop / snapshot.
    assert states._map_key("alice", "shared") != states._map_key("bob", "shared")  # noqa: SLF001
    # NUL separates the parts (name is pattern-validated so it can't contain one).
    assert states._map_key("alice", "shared") == "alice\x00shared"  # noqa: SLF001


def test_build_states_msg_shape() -> None:
    obj = ObjectState(object_id="host:h1", type="host", state="UP", output="ok")
    msg = states._build_states_msg(  # noqa: SLF001
        "b1",
        MapStates(
            map_name="b1",
            states=[],
            generated_at=0.0,
            dead_sites=["remote_fra"],
            runtime=get_daemon_runtime(),
        ),
        to_send=[obj],
        removed_ids=["host:gone"],
        full=True,
        timing=[ObjectTiming(object_id="host:h1")],
        ft_delta=None,
    )
    assert msg.map == "b1"
    assert msg.full is True
    assert msg.removed_ids == ["host:gone"]
    assert msg.states.dead_sites == ["remote_fra"]
    # A non-foldertree map carries no tree delta.
    assert msg.states.folder_tree_delta is None
    assert [s.object_id for s in msg.states.states] == ["host:h1"]
    # The daemon's runtime knobs ride along with the states it produces — the
    # client has no other source for the cadence it polls at when SSE is down.
    assert msg.states.runtime == get_daemon_runtime()


def test_the_api_description_names_each_event_with_the_schema_of_its_data() -> None:
    # The SPA's stream types are generated from this schema. An event that is not
    # in it leaves the client hand-typing the wire, which is where the drift the
    # generator exists to prevent creeps back in.
    schema = create_app().openapi()

    content = schema["paths"]["/api/v1/sse/maps/{name}"]["get"]["responses"]["200"]["content"]
    items = content["text/event-stream"]["itemSchema"]["oneOf"]
    assert {
        item["properties"]["event"]["const"]: item["properties"]["data"]["contentSchema"]["$ref"]
        for item in items
    } == {
        "state_update": "#/components/schemas/StateUpdateMessage",
        "topology_update": "#/components/schemas/TopologyUpdateMessage",
        "map_saved": "#/components/schemas/MapSavedMessage",
    }


# --------------------------------------------------------------------------- #
# registered_map — resolution
# --------------------------------------------------------------------------- #


def test_registered_map_returns_registered_config() -> None:
    map_service.register_map("alice", MapConfig(name="b1", alias="Map One"))
    cfg = deps.registered_map(Principal(name="alice"), "b1")
    assert cfg.name == "b1"


def test_registered_map_missing_map_is_404() -> None:
    with pytest.raises(HTTPException) as exc:
        deps.registered_map(Principal(name="alice"), "absent")
    assert exc.value.status_code == HTTPStatus.NOT_FOUND


# --------------------------------------------------------------------------- #
# _broadcast_loop — lifecycle + error resilience
# --------------------------------------------------------------------------- #


def test_broadcast_loop_exits_immediately_without_subscribers() -> None:
    # No subscriber → the while guard is false on entry, the loop returns at once
    # and the finally block cleans up (no lingering task registration).
    map_key = states._map_key("alice", "b1")  # noqa: SLF001
    asyncio.run(states._broadcast_loop(map_key, FakeLinkGui()))  # noqa: SLF001
    assert map_key not in states._broadcast_tasks  # noqa: SLF001


def test_broadcast_loop_survives_and_continues_after_a_failing_tick(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    map_key = states._map_key("alice", "b1")  # noqa: SLF001
    sub = manager.subscribe(map_key, None, folder_scope=None, group_key=None)

    monkeypatch.setattr(map_service, "get_map", lambda _owner, _name: MagicMock(name="cfg"))

    calls = {"n": 0}

    async def _boom(*_args: object, **_kwargs: object) -> MapStates:
        calls["n"] += 1
        raise RuntimeError("transient livestatus hiccup")

    monkeypatch.setattr(state_service, "get_map_states", _boom)
    monkeypatch.setattr(settings_service, "get_effective_state_refresh_interval", lambda: 0.0)

    sleeps = {"n": 0}

    async def _fake_sleep(_delay: float) -> None:
        sleeps["n"] += 1
        # Let the loop run a second full tick after the first failure, then end it.
        if sleeps["n"] >= 2:
            manager.unsubscribe(map_key, sub)

    monkeypatch.setattr(asyncio, "sleep", _fake_sleep)

    # Must not propagate the tick's RuntimeError, and must keep looping past it.
    asyncio.run(states._broadcast_loop(map_key, FakeLinkGui()))  # noqa: SLF001

    assert calls["n"] == 2  # a failing tick did not kill the loop; it ran again
    assert map_key not in states._broadcast_tasks  # noqa: SLF001


def test_broadcast_loop_newcomer_gets_full_established_gets_delta(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # A just-(re)joined subscriber must get a full built from the same fetch, while
    # established viewers get only the delta — so one client's reconnect never
    # re-fulls the whole group.
    map_key = states._map_key("alice", "b1")  # noqa: SLF001
    monkeypatch.setattr(map_service, "get_map", lambda _o, _n: MapConfig(name="b1"))

    # Prime the group snapshot as if an earlier tick had already run.
    state_service.compute_states_delta(
        map_key, None, [ObjectState(object_id="host:h1", type="host", state="UP", output="ok")]
    )

    established = manager.subscribe(map_key, None, group_key=None)
    established.needs_full = False
    newcomer = manager.subscribe(map_key, None, group_key=None)  # needs_full=True by default

    async def _states(*_a: object, **_k: object) -> MapStates:
        return MapStates(
            map_name="b1",
            states=[ObjectState(object_id="host:h1", type="host", state="DOWN", output="down")],
            generated_at=0.0,
            runtime=get_daemon_runtime(),
        )

    monkeypatch.setattr(state_service, "get_map_states", _states)
    monkeypatch.setattr(settings_service, "get_effective_state_refresh_interval", lambda: 0.0)

    async def _fake_sleep(_delay: float) -> None:
        manager.unsubscribe(map_key, established)
        manager.unsubscribe(map_key, newcomer)

    monkeypatch.setattr(asyncio, "sleep", _fake_sleep)
    asyncio.run(states._broadcast_loop(map_key, FakeLinkGui()))  # noqa: SLF001

    est_event = established.queue.get_nowait()
    new_event = newcomer.queue.get_nowait()
    assert (est_event.event, new_event.event) == ("state_update", "state_update")
    est_msg = json.loads(est_event.raw_data or "")
    new_msg = json.loads(new_event.raw_data or "")
    # Established viewer: a delta (state flipped UP -> DOWN), not a full.
    assert est_msg["full"] is False
    assert [s["object_id"] for s in est_msg["states"]["states"]] == ["host:h1"]
    # Newcomer: a full carrying the whole state set, and its flag is now cleared.
    assert new_msg["full"] is True
    assert newcomer.needs_full is False
    # Exactly one message each — the newcomer did not also force a group-wide full.
    assert established.queue.empty()
    assert newcomer.queue.empty()


@pytest.fixture
def _live_connection() -> Iterator[None]:
    state_service.register_connection("live_1", FakeConnection())
    yield
    state_service.unregister_connection("live_1")


@pytest.mark.usefixtures("_live_connection")
def test_pushed_topology_is_queued_as_a_topology_update_event() -> None:
    map_key = states._map_key("alice", "b1")  # noqa: SLF001
    sub = manager.subscribe(map_key, None)

    asyncio.run(
        states._push_topology_to(  # noqa: SLF001
            MapConfig(name="b1", connection_id="live_1"), map_key, None, [sub], force_full=True
        )
    )

    event = sub.queue.get_nowait()
    assert (event.event, json.loads(event.raw_data or "")["map"]) == ("topology_update", "b1")


# --------------------------------------------------------------------------- #
# SSE endpoint — connect-time authentication (before any streaming)
# --------------------------------------------------------------------------- #


@pytest.fixture
def gui() -> _GUI:
    return _GUI()


@pytest.fixture
def app(gui: _GUI, monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    monkeypatch.setenv("OMD_SITE", _SITE)
    app = FastAPI()
    app.include_router(states.router, prefix="/api/v1")
    app.state.gui_auth = gui.auth()
    return app


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app, raise_server_exceptions=True) as test_client:
        yield test_client


@pytest.mark.parametrize(
    "headers", [pytest.param({}, id="no cookie"), pytest.param(_session("forged"), id="refused")]
)
def test_sse_endpoint_rejects_a_missing_or_refused_session(
    client: TestClient, headers: dict[str, str]
) -> None:
    resp = client.get("/api/v1/sse/maps/b1", headers=headers)
    assert resp.status_code == HTTPStatus.UNAUTHORIZED


def test_sse_endpoint_refuses_a_map_the_user_does_not_see(client: TestClient, gui: _GUI) -> None:
    map_service.register_map("alice", MapConfig(name="b1"))
    gui.unpublished.add("b1")

    resp = client.get("/api/v1/sse/maps/b1", headers=_session("bob"))

    assert resp.status_code == HTTPStatus.NOT_FOUND


def test_sse_connect_limit_is_per_user(client: TestClient) -> None:
    # Every client reaches the daemon from the same proxy address, so the budget
    # has to follow the user: one user's reconnect storm must not lock out others.
    for _ in range(ws_connect_limiter._max):  # noqa: SLF001
        assert (
            client.get("/api/v1/sse/maps/b1", headers=_session("alice")).status_code
            == HTTPStatus.NOT_FOUND
        )
    assert (
        client.get("/api/v1/sse/maps/b1", headers=_session("alice")).status_code
        == HTTPStatus.TOO_MANY_REQUESTS
    )
    assert (
        client.get("/api/v1/sse/maps/b1", headers=_session("bob")).status_code
        == HTTPStatus.NOT_FOUND
    )


def test_sse_refused_sessions_do_not_count_toward_the_limit(client: TestClient) -> None:
    for _ in range(ws_connect_limiter._max):  # noqa: SLF001
        assert (
            client.get("/api/v1/sse/maps/b1", headers=_session("forged")).status_code
            == HTTPStatus.UNAUTHORIZED
        )
    assert (
        client.get("/api/v1/sse/maps/b1", headers=_session("alice")).status_code
        == HTTPStatus.NOT_FOUND
    )


def test_sse_rejects_when_the_concurrent_stream_cap_is_reached(client: TestClient) -> None:
    # A held stream pins an Apache worker for as long as it is open, so past the
    # per-user cap a further connect for a real map is refused before it opens.
    map_service.register_map("alice", MapConfig(name="b1"))
    held = 0
    try:
        while sse_stream_limiter.try_acquire("alice"):
            held += 1
        assert (
            client.get("/api/v1/sse/maps/b1", headers=_session("alice")).status_code
            == HTTPStatus.TOO_MANY_REQUESTS
        )
    finally:
        for _ in range(held):
            sse_stream_limiter.release("alice")


_INTERVAL = 60


class _CountedStates:
    """States of map b1 that count how often they were fetched, and for whom."""

    def __init__(self) -> None:
        self.fetched_for: list[str | None] = []
        self.release = asyncio.Event()
        self.release.set()
        self.fail = False
        self.on_fetch: Callable[[], None] = lambda: None

    async def __call__(self, cfg: MapConfig, *, auth_user: str | None, **_kw: object) -> MapStates:
        self.fetched_for.append(auth_user)
        await self.release.wait()
        self.on_fetch()
        if self.fail:
            raise RuntimeError("Livestatus went away")
        return MapStates(
            map_name=cfg.name,
            states=[
                ObjectState(
                    object_id="host:h1",
                    type="host",
                    state="UP",
                    output=f"fetch {len(self.fetched_for)}",
                )
            ],
            generated_at=0.0,
            runtime=get_daemon_runtime(),
        )


@pytest.fixture
def counted_states(monkeypatch: pytest.MonkeyPatch) -> _CountedStates:
    fetch = _CountedStates()
    monkeypatch.setattr(state_service, "get_map_states", fetch)
    monkeypatch.setattr(settings_service, "get_effective_state_refresh_interval", lambda: _INTERVAL)
    map_service.register_map("alice", MapConfig(name="b1"))
    return fetch


def _poll(client: TestClient, user: str, query: str = "") -> int:
    return client.get(f"/api/v1/maps/b1/states{query}", headers=_session(user)).status_code


def test_polls_of_one_user_within_the_interval_share_one_fetch(
    client: TestClient, counted_states: _CountedStates
) -> None:
    assert [_poll(client, "alice") for _ in range(3)] == [HTTPStatus.OK] * 3
    assert counted_states.fetched_for == ["alice"]


def _poll_together(
    app: FastAPI, counted_states: _CountedStates, monkeypatch: pytest.MonkeyPatch
) -> list[int]:
    counted_states.release.clear()
    joined: list[object] = []
    run = states._fetches.run  # noqa: SLF001

    async def _run(
        key: tuple[str, str | None, int],
        fetch: Callable[[], Awaitable[states._Flight]],
    ) -> states._Flight:
        joined.append(key)
        return await run(key, fetch)

    monkeypatch.setattr(states._fetches, "run", _run)  # noqa: SLF001

    async def _together() -> list[int]:
        async with httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=app), base_url="http://test"
        ) as client:
            polls = [
                asyncio.ensure_future(
                    client.get("/api/v1/maps/b1/states", headers=_session("alice"))
                )
                for _ in range(3)
            ]
            while len(joined) < len(polls):
                await asyncio.sleep(0)
            counted_states.release.set()
            return [r.status_code for r in await asyncio.gather(*polls)]

    return asyncio.run(_together())


def test_polls_that_arrive_together_share_the_fetch_under_way(
    app: FastAPI, counted_states: _CountedStates, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert _poll_together(app, counted_states, monkeypatch) == [HTTPStatus.OK] * 3
    assert counted_states.fetched_for == ["alice"]


def test_polls_of_users_who_see_differently_fetch_apart(
    client: TestClient, counted_states: _CountedStates
) -> None:
    _poll(client, "alice")
    _poll(client, "bob")
    assert counted_states.fetched_for == ["alice", "bob"]


def test_a_poll_after_the_interval_fetches_again(
    client: TestClient, counted_states: _CountedStates, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings_service, "get_effective_state_refresh_interval", lambda: 0)
    _poll(client, "alice")
    _poll(client, "alice")
    assert counted_states.fetched_for == ["alice", "alice"]


def test_a_poll_an_interval_after_the_query_began_fetches_again(
    client: TestClient, counted_states: _CountedStates, monkeypatch: pytest.MonkeyPatch
) -> None:
    now = [100.0]
    monkeypatch.setattr(states, "time", SimpleNamespace(monotonic=lambda: now[0]))
    counted_states.on_fetch = lambda: now.__setitem__(0, now[0] + _INTERVAL / 2)
    _poll(client, "alice")
    now[0] = 100.0 + _INTERVAL
    _poll(client, "alice")
    assert counted_states.fetched_for == ["alice", "alice"]


def test_a_poll_after_a_failed_fetch_fetches_again(
    client: TestClient, counted_states: _CountedStates
) -> None:
    counted_states.fail = True
    with pytest.raises(RuntimeError):
        _poll(client, "alice")
    counted_states.fail = False
    assert _poll(client, "alice") == HTTPStatus.OK
    assert counted_states.fetched_for == ["alice", "alice"]


def test_a_poll_with_unsaved_view_settings_fetches_them_itself(
    client: TestClient, counted_states: _CountedStates
) -> None:
    map_service.register_map("alice", MapConfig(name="b1", view=RadarView()))
    _poll(client, "alice")
    _poll(client, "alice", "?radar_filter=hostgroup&radar_filter_value=web")
    assert counted_states.fetched_for == ["alice", "alice"]


def _output_of_poll(client: TestClient) -> str:
    response = client.get("/api/v1/maps/b1/states", headers=_session("alice"))
    return str(response.json()["states"][0]["output"])


def _stream_ticks(
    monkeypatch: pytest.MonkeyPatch, ticks: int, between_ticks: Callable[[], None]
) -> None:
    map_key = states._map_key("alice", "b1")  # noqa: SLF001
    sub = manager.subscribe(map_key, "alice", group_key="alice")
    done = {"ticks": 0}
    sleep = asyncio.sleep

    # Only the loop's wait between ticks: the request a test polls with in
    # between may sleep too.
    async def _after_tick(delay: float) -> None:
        if delay != _INTERVAL:
            await sleep(delay)
            return
        between_ticks()
        done["ticks"] += 1
        if done["ticks"] == ticks:
            manager.unsubscribe(map_key, sub)

    with monkeypatch.context() as patched:
        patched.setattr(asyncio, "sleep", _after_tick)
        asyncio.run(states._broadcast_loop(map_key, FakeLinkGui()))  # noqa: SLF001


def test_polls_take_the_states_the_stream_fetched_after_a_poll(
    client: TestClient, counted_states: _CountedStates, monkeypatch: pytest.MonkeyPatch
) -> None:
    outputs = [_output_of_poll(client)]

    _stream_ticks(monkeypatch, 2, lambda: outputs.append(_output_of_poll(client)))

    assert outputs == ["fetch 1", "fetch 2", "fetch 3"]
    assert len(counted_states.fetched_for) == 3


def test_a_poll_while_the_stream_fetches_shares_that_fetch(
    app: FastAPI, counted_states: _CountedStates, monkeypatch: pytest.MonkeyPatch
) -> None:
    map_key = states._map_key("alice", "b1")  # noqa: SLF001
    sub = manager.subscribe(map_key, "alice", group_key="alice")
    counted_states.release.clear()
    joined: list[object] = []
    run = states._fetches.run  # noqa: SLF001
    sleep = asyncio.sleep

    async def _run(
        key: tuple[str, str | None, int],
        fetch: Callable[[], Awaitable[states._Flight]],
    ) -> states._Flight:
        joined.append(key)
        return await run(key, fetch)

    async def _after_tick(delay: float) -> None:
        if delay != _INTERVAL:
            await sleep(delay)
            return
        manager.unsubscribe(map_key, sub)

    async def _poll_during_the_tick() -> httpx2.Response:
        ticking = asyncio.ensure_future(states._broadcast_loop(map_key, FakeLinkGui()))  # noqa: SLF001
        async with httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=app), base_url="http://test"
        ) as client:
            poll = asyncio.ensure_future(
                client.get("/api/v1/maps/b1/states", headers=_session("alice"))
            )
            while len(joined) < 2:
                await sleep(0)
            counted_states.release.set()
            response = await poll
        await ticking
        return response

    monkeypatch.setattr(states._fetches, "run", _run)  # noqa: SLF001
    monkeypatch.setattr(asyncio, "sleep", _after_tick)
    response = asyncio.run(_poll_during_the_tick())

    assert response.json()["states"][0]["output"] == "fetch 1"
    assert len(counted_states.fetched_for) == 1


def test_a_stream_keeps_no_states_for_polls_nobody_asked_for(
    client: TestClient, counted_states: _CountedStates, monkeypatch: pytest.MonkeyPatch
) -> None:
    outputs: list[str] = []

    _stream_ticks(monkeypatch, 1, lambda: outputs.append(_output_of_poll(client)))

    assert outputs == ["fetch 2"]
    assert len(counted_states.fetched_for) == 2


def test_polls_of_a_map_too_large_to_keep_fetch_each(
    client: TestClient, counted_states: _CountedStates, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(states, "_FETCHED_MAX_OBJECTS", 0)
    _poll(client, "alice")
    _poll(client, "alice")
    assert counted_states.fetched_for == ["alice", "alice"]


def test_polls_of_a_map_too_large_to_keep_that_arrive_together_share_the_fetch(
    app: FastAPI, counted_states: _CountedStates, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(states, "_FETCHED_MAX_OBJECTS", 0)
    _poll_together(app, counted_states, monkeypatch)
    assert counted_states.fetched_for == ["alice"]


@pytest.mark.usefixtures("counted_states")
def test_a_poll_through_the_compressing_middleware_is_compressed_once(app: FastAPI) -> None:
    app.add_middleware(CompactGZipMiddleware, minimum_size=0, compresslevel=1)
    with TestClient(app) as client:
        response = client.get("/api/v1/maps/b1/states", headers=_session("alice"))
    assert response.headers["content-encoding"] == "gzip"
    assert response.json()["states"][0]["output"] == "fetch 1"


@pytest.mark.usefixtures("counted_states")
def test_a_poll_of_a_client_without_gzip_gets_the_states_uncompressed(client: TestClient) -> None:
    response = client.get(
        "/api/v1/maps/b1/states", headers={**_session("alice"), "Accept-Encoding": "identity"}
    )
    assert "content-encoding" not in response.headers
    assert response.json()["states"][0]["output"] == "fetch 1"


def _spend_read_budget_but_one(user: str, limiter: RateLimiter = rest_read_limiter) -> None:
    for _ in range(limiter._max - len(limiter._calls[user]) - 1):  # noqa: SLF001
        limiter.record(user)


@pytest.mark.usefixtures("counted_states")
def test_polls_answered_from_the_states_kept_spend_no_read_budget(client: TestClient) -> None:
    _poll(client, "alice")
    _spend_read_budget_but_one("alice")
    assert [_poll(client, "alice") for _ in range(3)] == [HTTPStatus.OK] * 3


@pytest.mark.usefixtures("counted_states")
def test_polls_answered_from_the_states_kept_spend_a_budget_of_their_own(
    client: TestClient,
) -> None:
    _poll(client, "alice")
    _spend_read_budget_but_one("alice", kept_states_limiter)
    assert [_poll(client, "alice") for _ in range(2)] == [
        HTTPStatus.OK,
        HTTPStatus.TOO_MANY_REQUESTS,
    ]


@pytest.mark.usefixtures("counted_states")
def test_polls_that_fetch_spend_read_budget(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings_service, "get_effective_state_refresh_interval", lambda: 0)
    _spend_read_budget_but_one("alice")
    assert [_poll(client, "alice") for _ in range(2)] == [
        HTTPStatus.OK,
        HTTPStatus.TOO_MANY_REQUESTS,
    ]


def test_a_poll_with_unsaved_view_settings_leaves_the_registered_map_alone(
    client: TestClient,
) -> None:
    map_service.register_map("alice", MapConfig(name="b1", view=RadarView()))
    client.get(
        "/api/v1/maps/b1/states?radar_filter=hostgroup&radar_filter_value=web",
        headers=_session("alice"),
    )
    registered = map_service.get_map("alice", "b1")
    assert registered is not None
    assert registered.view == RadarView()


def _subscription(gui: _GUI, user: str) -> states.StreamSubscription:
    return states.StreamSubscription(
        subscriber=MagicMock(spec=Subscriber),
        name="b1",
        user=Principal(name=user).viewing("alice", "b1"),
        auth=gui.auth(),
        session_cookie=user,
    )


def _still_holds(subscription: states.StreamSubscription) -> bool:
    return asyncio.run(states.session_still_holds(subscription))


def test_the_session_cookie_of_a_stream_stays_out_of_its_repr(gui: _GUI) -> None:
    subscription = states.StreamSubscription(
        subscriber=MagicMock(spec=Subscriber),
        name="b1",
        user=Principal(name="alice").viewing("alice", "b1"),
        auth=gui.auth(),
        session_cookie="alice:do-not-leak",
    )
    assert "do-not-leak" not in repr(subscription)


def test_an_open_stream_holds_while_the_session_does(gui: _GUI) -> None:
    assert _still_holds(_subscription(gui, "alice"))


def test_an_open_stream_ends_once_its_user_logged_out(gui: _GUI) -> None:
    gui.logged_out.add("alice")
    assert not _still_holds(_subscription(gui, "alice"))


def test_an_open_stream_ends_once_its_map_is_gone_for_the_user(gui: _GUI) -> None:
    gui.unpublished.add("b1")
    assert not _still_holds(_subscription(gui, "alice"))


def test_an_open_stream_ends_once_the_scope_of_its_user_changed(gui: _GUI) -> None:
    subscription = _subscription(gui, "alice")
    with_more_scope = states.StreamSubscription(
        subscriber=subscription.subscriber,
        name=subscription.name,
        user=Principal(name="alice", see_all=True).viewing("alice", "b1"),
        auth=subscription.auth,
        session_cookie=subscription.session_cookie,
    )
    assert not _still_holds(with_more_scope)


def test_an_open_stream_goes_on_without_a_verdict_of_the_gui(gui: _GUI) -> None:
    gui.down = True
    assert _still_holds(_subscription(gui, "alice"))


# --------------------------------------------------------------------------- #
# SSE endpoint — the open stream
# --------------------------------------------------------------------------- #


async def _stream_map_b1(
    app: FastAPI,
    user: str,
    *,
    leave_after_events: int | None = None,
    leave_after_keepalives: int | None = None,
    on_event: Callable[[], None] = lambda: None,
) -> bytes:
    """Drives the stream of map b1 as a client that calls on_event for each event it
    receives and leaves once it has received leave_after_events events or
    leave_after_keepalives keep-alive comments, and returns what it received.
    TestClient cannot: it waits for the response to end, which an open stream never
    does."""
    received = bytearray()
    left = asyncio.Event()

    def leave_when_done() -> None:
        frames = bytes(received).split(b"\n\n")[:-1]
        comments = sum(1 for frame in frames if frame.startswith(b":"))
        keepalives = frames.count(b": ping")
        if (leave_after_events is not None and len(frames) - comments >= leave_after_events) or (
            leave_after_keepalives is not None and keepalives >= leave_after_keepalives
        ):
            left.set()

    async def receive() -> Message:
        await left.wait()
        return {"type": "http.disconnect"}

    async def send(message: Message) -> None:
        if message["type"] == "http.response.body" and message.get("body"):
            received.extend(message["body"])
            on_event()
        leave_when_done()

    leave_when_done()
    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/api/v1/sse/maps/b1",
        "raw_path": b"/api/v1/sse/maps/b1",
        "root_path": "",
        "query_string": b"",
        "headers": [(b"cookie", f"auth_{_SITE}={user}".encode())],
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
    }
    await app(scope, receive, send)
    return bytes(received)


@pytest.mark.usefixtures("_live_connection")
def test_sse_sends_each_message_as_an_event_with_its_name_and_data(app: FastAPI) -> None:
    map_service.register_map("alice", MapConfig(name="b1", view=FlowView()))

    received = asyncio.run(_stream_map_b1(app, "alice", leave_after_events=2))

    events = [
        dict(line.split(": ", 1) for line in frame.splitlines())
        for frame in received.decode().split("\n\n")
        if frame and not frame.startswith(":")
    ][:2]
    assert sorted((e["event"], json.loads(e["data"])["type"]) for e in events) == [
        ("state_update", "state_update"),
        ("topology_update", "topology_update"),
    ]


def test_sse_writes_to_an_idle_stream(app: FastAPI, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(states, "_KEEPALIVE_INTERVAL", 0.01)
    map_service.register_map("alice", MapConfig(name="b1"))

    received = asyncio.run(_stream_map_b1(app, "alice", leave_after_keepalives=1))

    assert b": ping\n\n" in received


def _free_stream_slots(user: str) -> int:
    free = 0
    while sse_stream_limiter.try_acquire(user):
        free += 1
    for _ in range(free):
        sse_stream_limiter.release(user)
    return free


@pytest.mark.parametrize("leave_after_events", [0, 1])
def test_sse_releases_the_subscriber_and_stream_slot_when_the_client_leaves(
    app: FastAPI, leave_after_events: int
) -> None:
    map_service.register_map("alice", MapConfig(name="b1"))
    free_slots = _free_stream_slots("alice")

    asyncio.run(_stream_map_b1(app, "alice", leave_after_events=leave_after_events))

    assert (
        manager.get_subscriber_count(states._map_key("alice", "b1")),  # noqa: SLF001
        _free_stream_slots("alice"),
    ) == (0, free_slots)


def _overflow_the_subscribers_of_b1() -> None:
    map_key = states._map_key("alice", "b1")  # noqa: SLF001
    filler: SentEvent[StreamMessage] = SentEvent(event="state_update", raw_data="{}")
    for subscribers in manager.get_subscribers_grouped(map_key).values():
        for subscriber in subscribers:
            while not subscriber.overflowed:
                manager.push(map_key, [subscriber], filler)


def test_sse_releases_the_subscriber_and_stream_slot_when_the_subscriber_overflows(
    app: FastAPI,
) -> None:
    map_service.register_map("alice", MapConfig(name="b1"))
    free_slots = _free_stream_slots("alice")

    asyncio.run(_stream_map_b1(app, "alice", on_event=_overflow_the_subscribers_of_b1))

    assert (
        manager.get_subscriber_count(states._map_key("alice", "b1")),  # noqa: SLF001
        _free_stream_slots("alice"),
    ) == (0, free_slots)


def test_sse_releases_the_subscriber_and_stream_slot_when_the_daemon_stops(app: FastAPI) -> None:
    map_service.register_map("alice", MapConfig(name="b1"))
    free_slots = _free_stream_slots("alice")

    asyncio.run(_stream_map_b1(app, "alice", on_event=manager.close_all))

    assert (
        manager.get_subscriber_count(states._map_key("alice", "b1")),  # noqa: SLF001
        _free_stream_slots("alice"),
    ) == (0, free_slots)


def test_a_see_all_user_shares_no_folder_tree_with_a_user_named_none() -> None:
    scope = FolderScope(see_all=False, groups=frozenset({"ops"}))

    see_all = states._Audience(None, scope).group_key  # noqa: SLF001
    named_none = states._Audience("None", scope).group_key  # noqa: SLF001

    assert see_all != named_none
