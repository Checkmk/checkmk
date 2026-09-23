#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""SSE streaming layer of the states router.

The per-(map, auth_user) *delta* computation is covered by
``test_state_service_resolution.py``; what was untested is the layer that drives
it: the shared broadcast loop, its error resilience, the map-key isolation, and
the connect-time auth on the ``?token=`` SSE endpoint. Those are the parts that
run unattended and, if they regress, silently freeze or cross-wire live maps.

Async coroutines are driven with ``asyncio.run`` (no asyncio plugin in this
target); the loop is bounded by unsubscribing the sole subscriber from a patched
``asyncio.sleep`` so it exits deterministically instead of running forever.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import time
from collections.abc import Iterator
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from cmk.maps.backend.api.v1 import states
from cmk.maps.backend.app import create_app
from cmk.maps.backend.core.auth import Principal
from cmk.maps.backend.core.ratelimit import ws_connect_limiter
from cmk.maps.backend.core.sse import manager
from cmk.maps.backend.schemas.map import MapConfig
from cmk.maps.backend.schemas.state import MapStates, ObjectState, ObjectTiming
from cmk.maps.backend.services import map_service, settings_service, state_service
from cmk.maps.backend.services.settings_service import get_daemon_runtime
from cmk.maps.shared.ticket import (
    encode_ticket,
    MapClaim,
    STREAM_TICKET_AUDIENCE,
    StreamCapabilities,
)

pytestmark = pytest.mark.usefixtures("_shared_secret", "_clear_stream_state")

_KEY = b"0123456789abcdef0123456789abcdef"
_STREAM_CAPS = StreamCapabilities(see_all=False, folder_see_all=False, contact_groups=[])
_MAP_CLAIM = MapClaim(owner="alice", name="b1")


class _FakeSecret:
    def hmac(self, msg: bytes) -> bytes:
        return hmac.new(_KEY, msg, hashlib.sha256).digest()


class _FakeSiteInternalSecret:
    @property
    def secret(self) -> _FakeSecret:
        return _FakeSecret()


@pytest.fixture
def _shared_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    """Let ``principal_from_token`` fail closed to None on a bad token instead of
    raising FileNotFoundError for the missing site secret."""
    monkeypatch.setattr(
        "cmk.maps.backend.core.auth.SiteInternalSecret", _FakeSiteInternalSecret, raising=True
    )


@pytest.fixture
def _clear_stream_state() -> Iterator[None]:
    """The shared conftest clears map/snapshot state; also drop SSE subscribers
    and per-map broadcast bookkeeping so streams don't bleed across tests."""
    yield
    manager._subscribers.clear()  # noqa: SLF001
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
    msg = json.loads(
        states._build_states_msg(  # noqa: SLF001
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
    )
    assert msg["type"] == "state_update"
    assert msg["map"] == "b1"
    assert msg["full"] is True
    assert msg["removed_ids"] == ["host:gone"]
    assert msg["states"]["dead_sites"] == ["remote_fra"]
    # A non-foldertree map carries no tree delta.
    assert msg["states"]["folder_tree_delta"] is None
    assert [s["object_id"] for s in msg["states"]["states"]] == ["host:h1"]
    # The daemon's runtime knobs ride along with the states it produces — the
    # client has no other source for the cadence it polls at when SSE is down.
    assert msg["states"]["runtime"] == get_daemon_runtime().model_dump()


def test_stream_frames_are_published_in_the_schema() -> None:
    # The SPA's stream types are generated from this schema. A frame that is not
    # in it leaves the client hand-typing the wire, which is where the drift the
    # generator exists to prevent creeps back in.
    schema = create_app().openapi()
    assert "StateUpdateMessage" in schema["components"]["schemas"]
    assert "TopologyUpdateMessage" in schema["components"]["schemas"]
    stream = schema["paths"]["/api/v1/sse/maps/{name}"]["get"]
    content = stream["responses"]["200"]["content"]
    assert list(content) == ["text/event-stream"]
    assert content["text/event-stream"]["schema"]["anyOf"] == [
        {"$ref": "#/components/schemas/StateUpdateMessage"},
        {"$ref": "#/components/schemas/TopologyUpdateMessage"},
    ]


# --------------------------------------------------------------------------- #
# _map_for_stream — resolution + map-scoped ticket binding
# --------------------------------------------------------------------------- #


def test_map_for_stream_returns_registered_config() -> None:
    map_service.register_map("alice", MapConfig(name="b1", alias="Map One"))
    cfg = states._map_for_stream(Principal(name="alice"), "b1")  # noqa: SLF001
    assert cfg.name == "b1"


def test_map_for_stream_missing_map_is_404() -> None:
    with pytest.raises(HTTPException) as exc:
        states._map_for_stream(Principal(name="alice"), "absent")  # noqa: SLF001
    assert exc.value.status_code == 404


def test_map_for_stream_map_scoped_ticket_rejects_other_map() -> None:
    # A ticket minted for one map must not be usable to stream another, even if
    # that other map exists under the same resolved owner.
    map_service.register_map("alice", MapConfig(name="other"))
    scoped = Principal(name="alice", map_owner="alice", map_name="shared")
    with pytest.raises(HTTPException) as exc:
        states._map_for_stream(scoped, "other")  # noqa: SLF001
    assert exc.value.status_code == 404


# --------------------------------------------------------------------------- #
# _broadcast_loop — lifecycle + error resilience
# --------------------------------------------------------------------------- #


def test_broadcast_loop_exits_immediately_without_subscribers() -> None:
    # No subscriber → the while guard is false on entry, the loop returns at once
    # and the finally block cleans up (no lingering task registration).
    map_key = states._map_key("alice", "b1")  # noqa: SLF001
    asyncio.run(states._broadcast_loop(map_key))  # noqa: SLF001
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
    asyncio.run(states._broadcast_loop(map_key))  # noqa: SLF001

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
    asyncio.run(states._broadcast_loop(map_key))  # noqa: SLF001

    est_msg = json.loads(established.queue.get_nowait())
    new_msg = json.loads(newcomer.queue.get_nowait())
    # Established viewer: a delta (state flipped UP -> DOWN), not a full.
    assert est_msg["full"] is False
    assert [s["object_id"] for s in est_msg["states"]["states"]] == ["host:h1"]
    # Newcomer: a full carrying the whole state set, and its flag is now cleared.
    assert new_msg["full"] is True
    assert newcomer.needs_full is False
    # Exactly one message each — the newcomer did not also force a group-wide full.
    assert established.queue.empty()
    assert newcomer.queue.empty()


# --------------------------------------------------------------------------- #
# SSE endpoint — connect-time authentication (before any streaming)
# --------------------------------------------------------------------------- #


@pytest.fixture
def client() -> Iterator[TestClient]:
    app = FastAPI()
    app.include_router(states.router, prefix="/api/v1")
    with TestClient(app, raise_server_exceptions=True) as test_client:
        yield test_client


def test_sse_endpoint_rejects_invalid_token(client: TestClient) -> None:
    resp = client.get("/api/v1/sse/maps/b1?token=not-a-valid-ticket")
    assert resp.status_code == 401


def _stream_token(user: str) -> str:
    return encode_ticket(
        {"sub": user, "exp": int(time.time()) + 300, "caps": _STREAM_CAPS, "map": _MAP_CLAIM},
        _FakeSecret().hmac,
        audience=STREAM_TICKET_AUDIENCE,
    )


def test_sse_connect_limit_is_per_user(client: TestClient) -> None:
    # Every client reaches the daemon from the same proxy address, so the budget
    # has to follow the user: one user's reconnect storm must not lock out others.
    alice, bob = _stream_token("alice"), _stream_token("bob")
    for _ in range(ws_connect_limiter._max):  # noqa: SLF001
        assert client.get(f"/api/v1/sse/maps/b1?token={alice}").status_code == 404
    assert client.get(f"/api/v1/sse/maps/b1?token={alice}").status_code == 429
    assert client.get(f"/api/v1/sse/maps/b1?token={bob}").status_code == 404


def test_sse_invalid_tokens_do_not_count_toward_the_limit(client: TestClient) -> None:
    for _ in range(ws_connect_limiter._max):  # noqa: SLF001
        assert client.get("/api/v1/sse/maps/b1?token=forged").status_code == 401
    assert client.get(f"/api/v1/sse/maps/b1?token={_stream_token('alice')}").status_code == 404
