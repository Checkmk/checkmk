#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import asyncio
import itertools
import threading
from collections.abc import Iterator, Mapping
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import Mock

import pytest

from cmk.livestatus_client import MultiSiteConnection, SingleSiteConnection
from cmk.maps.backend.connections import livestatus
from cmk.maps.backend.connections.base import MonitoringScope, QueryTimeoutError
from cmk.maps.backend.core.config import settings
from cmk.maps.backend.integrations import checkmk_sites
from cmk.maps.backend.schemas.state import ObjectState


class _Client:
    def __init__(self, answer: threading.Event) -> None:
        self._answer = answer
        self.headers: list[str] = []

    def query(self, _query: object, add_headers: str = "") -> list[object]:
        self.headers.append(add_headers)
        self._answer.wait()
        return []

    def disconnect(self) -> None: ...


@pytest.fixture(name="answer")
def fixture_answer() -> Iterator[threading.Event]:
    answer = threading.Event()
    yield answer
    answer.set()


def _connection(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, client: _Client
) -> livestatus.LivestatusConnection:
    monkeypatch.setattr(settings, "checkmk_omd_root", str(tmp_path))
    monkeypatch.setattr(checkmk_sites, "load_sites", lambda: None)
    conn = livestatus.LivestatusConnection(
        socket_path=str(tmp_path / "tmp" / "run" / "live"), host=None
    )
    monkeypatch.setattr(conn, "_make_singlesite_connection", lambda: client)
    return conn


def test_a_query_without_an_answer_leaves_the_default_executor_free(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, answer: threading.Event
) -> None:
    monkeypatch.setattr(settings, "connection_query_timeout", 1)
    conn = _connection(monkeypatch, tmp_path, _Client(answer))

    async def scenario() -> str:
        loop = asyncio.get_running_loop()
        loop.set_default_executor(ThreadPoolExecutor(max_workers=1))
        with pytest.raises(QueryTimeoutError):
            await conn._query_with_site("GET hosts\nColumns: name\n")  # noqa: SLF001
        return await asyncio.wait_for(loop.run_in_executor(None, lambda: "free"), timeout=1)

    assert asyncio.run(scenario()) == "free"


def _site_answering_when(answer: threading.Event, headers: list[str]) -> SingleSiteConnection:
    def _query(_query: object, add_headers: str = "") -> list[object]:
        headers.append(add_headers)
        answer.wait()
        return []

    site = Mock(spec=SingleSiteConnection)
    site.query.side_effect = _query
    return site


def _tcp_connection(
    answer: threading.Event, headers: list[str] | None = None
) -> livestatus.LivestatusConnection:
    site = _site_answering_when(answer, [] if headers is None else headers)
    return livestatus.LivestatusConnection(
        host="10.0.0.1", make_site_connection=lambda *_args, **_kwargs: site
    )


def test_a_query_on_a_closed_connection_times_out(answer: threading.Event) -> None:
    answer.set()
    conn = _tcp_connection(answer)
    conn.close()

    with pytest.raises(QueryTimeoutError):
        asyncio.run(conn.get_all_hosts_states())


def test_the_user_reaches_the_query_thread(answer: threading.Event) -> None:
    answer.set()
    headers: list[str] = []
    conn = _tcp_connection(answer, headers)

    async def scenario() -> None:
        async with conn.with_monitoring_scope(MonitoringScope("jdoe")):
            await conn.get_all_hosts_states()

    asyncio.run(scenario())

    assert headers == ["AuthUser: jdoe\n"]


def _remote_answering_when(
    answer: threading.Event,
    asked: threading.Event,
    dead_sites: Iterator[Mapping[str, Mapping[str, object]]] | None = None,
) -> MultiSiteConnection:
    def _query(_query: object, add_headers: str = "") -> list[object]:  # noqa: ARG001
        asked.set()
        answer.wait()
        return []

    remote = Mock(spec=MultiSiteConnection)
    remote.connections = []
    remote.query.side_effect = _query
    remote.dead_sites.side_effect = itertools.repeat({}) if dead_sites is None else dead_sites
    return remote


def _answered() -> threading.Event:
    answered = threading.Event()
    answered.set()
    return answered


def _federated(
    remotes: Iterator[MultiSiteConnection], *, federated_connections: int = 4
) -> tuple[livestatus.LivestatusConnection, list[MultiSiteConnection]]:
    built: list[MultiSiteConnection] = []

    def _connect(*_args: object, **_kwargs: object) -> MultiSiteConnection:
        built.append(remote := next(remotes))
        return remote

    conn = livestatus.LivestatusConnection(
        socket_path=str(Path(settings.checkmk_omd_root) / "tmp" / "run" / "live"),
        host=None,
        make_federated_connection=_connect,
        load_sites=lambda: {"central": {}, "remote1": {}},
        sites_mtime=lambda: 1.0,
        query_timeout=1,
        federated_connections=federated_connections,
    )
    return conn, built


def test_a_slow_remote_site_holds_up_no_other_query(answer: threading.Event) -> None:
    asked = threading.Event()
    conn, _built = _federated(
        iter(
            [
                _remote_answering_when(answer, asked),
                _remote_answering_when(_answered(), threading.Event()),
            ]
        )
    )

    async def scenario() -> dict[str, ObjectState]:
        slow = asyncio.create_task(conn.get_all_hosts_states())
        await asyncio.to_thread(asked.wait, 1)
        fast = await conn.get_all_hosts_states()
        answer.set()
        await slow
        return fast

    assert asyncio.run(scenario()) == {}


def test_a_connection_busy_while_a_site_recovers_does_not_mark_it_dead_again(
    answer: threading.Event,
) -> None:
    asked = threading.Event()
    dead = {"remote1": {"exception": "timed out"}}
    conn, _built = _federated(
        iter(
            [
                _remote_answering_when(answer, asked, itertools.repeat(dead)),
                _remote_answering_when(
                    _answered(), threading.Event(), itertools.chain([dead], itertools.repeat({}))
                ),
            ]
        )
    )

    async def scenario() -> list[str]:
        slow = asyncio.create_task(conn.get_all_hosts_states())
        await asyncio.to_thread(asked.wait, 1)
        await conn.get_all_hosts_states()
        seen_dead = conn.dead_sites()
        await conn.get_all_hosts_states()
        answer.set()
        await slow
        return seen_dead

    assert asyncio.run(scenario()) == ["remote1"]
    assert conn.dead_sites() == []


def test_a_query_finding_every_federated_connection_busy_times_out(
    answer: threading.Event,
) -> None:
    asked = threading.Event()
    conn, _built = _federated(
        iter(
            [
                _remote_answering_when(answer, asked),
                _remote_answering_when(_answered(), threading.Event()),
            ]
        ),
        federated_connections=1,
    )

    async def scenario() -> None:
        slow = asyncio.create_task(conn.get_all_hosts_states())
        await asyncio.to_thread(asked.wait, 1)
        try:
            await conn.get_all_hosts_states()
        finally:
            answer.set()
            await asyncio.gather(slow, return_exceptions=True)

    with pytest.raises(QueryTimeoutError):
        asyncio.run(scenario())


def test_no_more_federated_connections_are_opened_than_configured(
    answer: threading.Event,
) -> None:
    conn, built = _federated(
        (_remote_answering_when(answer, threading.Event()) for _ in itertools.count()),
        federated_connections=2,
    )

    async def scenario() -> None:
        await asyncio.gather(
            *(conn.get_all_hosts_states() for _ in range(3)), return_exceptions=True
        )

    asyncio.run(scenario())

    assert len(built) == 2
