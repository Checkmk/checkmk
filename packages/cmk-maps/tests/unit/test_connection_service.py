#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Runtime side of the connection service: config loading + the warmup loop.

The warmup loop pre-primes each connection's Livestatus pool in the background so
the first user-facing ``/topology`` call is fast. It runs unattended for the life
of the daemon, so its two contracts matter: it must never crash the loop on a
single flaky connection, and it must prime exactly the top-K hosts a flow map
will request (same ranking as the REST endpoint). Neither was covered before.

Async coroutines are driven with ``asyncio.run`` — the cmk-maps test target
has no asyncio plugin, matching ``test_state_service_resolution.py``.
"""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from typing import override

import pytest
from fake_connection import FakeConnection

from cmk.maps.backend.connections.base import ServiceRow, TopologyRow
from cmk.maps.backend.connections.livestatus import LivestatusConnection
from cmk.maps.backend.core.config import settings
from cmk.maps.backend.integrations import checkmk_globals
from cmk.maps.backend.schemas.connection import ConnectionConfig
from cmk.maps.backend.schemas.state import ServicesSummary
from cmk.maps.backend.services import connection_forms, connection_service, state_service

pytestmark = pytest.mark.usefixtures("_clear_connections")


@pytest.fixture
def _clear_connections() -> Iterator[None]:
    """The shared conftest clears map/snapshot state but not the connection
    registry — a connection one warmup test registers must not bleed into the next."""
    yield
    state_service._connections.clear()  # noqa: SLF001


class _StopLoop(Exception):
    """Sentinel raised from the patched sleep to break the otherwise-infinite loop."""


class _SpyConnection(FakeConnection):
    """Records topology/batch calls so the warmup contract can be asserted.

    Subclasses the demo connection so all abstract methods stay implemented; only
    the two calls the warmup tick makes are instrumented (optionally failing).
    """

    def __init__(self, *, topology: list[TopologyRow], fail_topology: bool = False) -> None:
        self._topology = topology
        self._fail_topology = fail_topology
        self.topology_calls = 0
        self.batched_hosts: list[list[str]] = []

    @override
    async def get_topology(self) -> list[TopologyRow]:
        self.topology_calls += 1
        if self._fail_topology:
            raise RuntimeError("stale socket")
        return self._topology

    @override
    async def get_hosts_services_batch(self, hostnames: list[str]) -> dict[str, list[ServiceRow]]:
        self.batched_hosts.append(list(hostnames))
        return {}


def _row(name: str, *, critical: int = 0, warning: int = 0) -> TopologyRow:
    return {
        "name": name,
        "parents": [],
        "state": "UP",
        "output": "",
        "services_summary": ServicesSummary(critical=critical, warning=warning),
    }


def test_warmup_tick_prefetches_topology_and_top_k_batch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "flow_map_top_affected_hosts", 2)
    spy = _SpyConnection(
        topology=[
            _row("calm", critical=0),
            _row("worst", critical=5),
            _row("middle", warning=3),
        ]
    )
    state_service.register_connection("c1", spy)

    asyncio.run(connection_service._warmup_tick())  # noqa: SLF001

    assert spy.topology_calls == 1
    # The bulk-services prefetch must target exactly the two highest-ranked hosts
    # (CRIT-weighted), in descending rank, so warmup primes what the flow map asks for.
    assert spy.batched_hosts == [["worst", "middle"]]


def test_warmup_tick_skips_batch_when_top_k_is_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "flow_map_top_affected_hosts", 0)
    spy = _SpyConnection(topology=[_row("h1", critical=1)])
    state_service.register_connection("c1", spy)

    asyncio.run(connection_service._warmup_tick())  # noqa: SLF001

    assert spy.topology_calls == 1
    assert spy.batched_hosts == []


def test_warmup_tick_skips_batch_when_topology_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "flow_map_top_affected_hosts", 5)
    spy = _SpyConnection(topology=[])
    state_service.register_connection("c1", spy)

    asyncio.run(connection_service._warmup_tick())  # noqa: SLF001

    assert spy.topology_calls == 1
    assert spy.batched_hosts == []


def test_warmup_tick_isolates_a_failing_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "flow_map_top_affected_hosts", 1)
    broken = _SpyConnection(topology=[_row("x", critical=1)], fail_topology=True)
    healthy = _SpyConnection(topology=[_row("ok", critical=1)])
    state_service.register_connection("broken", broken)
    state_service.register_connection("healthy", healthy)

    # A single connection raising must not abort the tick: the healthy one is
    # still primed. The tick swallows the exception rather than propagating.
    asyncio.run(connection_service._warmup_tick())  # noqa: SLF001

    assert broken.topology_calls == 1
    assert healthy.batched_hosts == [["ok"]]


def test_warmup_tick_skips_absent_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    # A connection id can be listed while ``get_connection`` returns None (dropped
    # between calls); the tick must skip it, not dereference None.
    monkeypatch.setattr(state_service, "list_connection_ids", lambda: ["ghost"])
    monkeypatch.setattr(state_service, "get_connection", lambda _cid: None)

    asyncio.run(connection_service._warmup_tick())  # must not raise  # noqa: SLF001


def test_warmup_loop_disabled_when_interval_not_positive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "connection_warmup_interval", 0)
    ticks = 0

    async def _counting_tick() -> None:
        nonlocal ticks
        ticks += 1

    monkeypatch.setattr(connection_service, "_warmup_tick", _counting_tick)

    asyncio.run(connection_service.warmup_loop())

    assert ticks == 0


def test_warmup_loop_primes_immediately_then_ticks_each_interval(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "connection_warmup_interval", 30)
    ticks = 0

    async def _counting_tick() -> None:
        nonlocal ticks
        ticks += 1

    sleeps: list[float] = []

    async def _fake_sleep(delay: float) -> None:
        sleeps.append(delay)
        # Let the loop run one full iteration, then break out of the otherwise-
        # infinite loop on the second sleep.
        if len(sleeps) >= 2:
            raise _StopLoop

    monkeypatch.setattr(connection_service, "_warmup_tick", _counting_tick)
    monkeypatch.setattr(asyncio, "sleep", _fake_sleep)

    with pytest.raises(_StopLoop):
        asyncio.run(connection_service.warmup_loop())

    # One immediate prime + one per elapsed interval, always sleeping the
    # configured interval between ticks.
    assert ticks == 2
    assert sleeps == [30, 30]


def test_load_all_falls_back_to_local_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "checkmk_site", "mysite")
    monkeypatch.setattr(settings, "checkmk_omd_root", "/omd/sites/mysite")
    monkeypatch.setattr(checkmk_globals, "load_maps_globals", dict)

    configs = connection_service.load_all()

    assert len(configs) == 1
    local = configs[0]
    assert local.id == "cmk_mysite"
    assert local.type == "livestatus"
    assert local.socket_path == "/omd/sites/mysite/tmp/run/live"


def test_load_all_returns_configured_connections(monkeypatch: pytest.MonkeyPatch) -> None:
    # The WATO-form flatten is covered by ``test_connection_forms.py``; here we
    # only pin that load_all returns the parsed connections instead of the
    # local-site fallback when the global is populated.
    configured = [
        ConnectionConfig(id="remote_dc", type="livestatus", label="Remote DC", host="10.0.0.9")
    ]
    monkeypatch.setattr(
        checkmk_globals,
        "load_maps_globals",
        lambda: {checkmk_globals.VAR_CONNECTIONS: [{"any": "raw"}]},
    )
    monkeypatch.setattr(connection_forms, "connections_from_global", lambda _raw: configured)

    configs = connection_service.load_all()

    assert [c.id for c in configs] == ["remote_dc"]
    assert configs[0].host == "10.0.0.9"


def test_build_instance_carries_connection_config() -> None:
    cfg = ConnectionConfig(
        id="tcp",
        type="livestatus",
        label="TCP remote",
        host="198.51.100.7",
        port=6560,
        tls=True,
        tls_verify=True,
        checkmk_url="https://remote/cmk",
        automation_user="automation",
    )

    instance = connection_service.build_instance(cfg)

    assert isinstance(instance, LivestatusConnection)
    assert instance._checkmk_url == "https://remote/cmk"  # noqa: SLF001
    assert instance._tls_verify is True  # noqa: SLF001
    # TLS applies only on the TCP path (host set) — mirror the connection's own rule.
    assert instance._use_tls is True  # noqa: SLF001
    assert instance._automation_user == "automation"  # noqa: SLF001


def test_activate_all_isolates_a_failing_connection(monkeypatch: pytest.MonkeyPatch) -> None:
    good = ConnectionConfig(id="good", type="livestatus", label="Good", socket_path="/tmp/live")
    bad = ConnectionConfig(id="bad", type="livestatus", label="Bad", socket_path="/tmp/live")
    monkeypatch.setattr(connection_service, "load_all", lambda: [bad, good])

    def _build(cfg: ConnectionConfig) -> object:
        if cfg.id == "bad":
            raise RuntimeError("cannot build")
        return FakeConnection()

    monkeypatch.setattr(connection_service, "build_instance", _build)

    # One connection failing to build must not stop the others from registering.
    connection_service.activate_all()

    assert state_service.get_connection("good") is not None
    assert state_service.get_connection("bad") is None
