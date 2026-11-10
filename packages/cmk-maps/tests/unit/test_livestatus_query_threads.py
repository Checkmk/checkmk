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

import pytest

from cmk.maps.backend.connections import livestatus
from cmk.maps.backend.connections.base import MonitoringScope, QueryTimeoutError
from cmk.maps.backend.core.config import settings
from cmk.maps.backend.integrations import checkmk_sites


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


def test_a_query_on_a_closed_connection_times_out(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, answer: threading.Event
) -> None:
    answer.set()
    conn = _connection(monkeypatch, tmp_path, _Client(answer))
    conn.close()

    with pytest.raises(QueryTimeoutError):
        asyncio.run(conn._query_with_site("GET hosts\nColumns: name\n"))  # noqa: SLF001


def test_the_user_reaches_the_query_thread(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, answer: threading.Event
) -> None:
    answer.set()
    client = _Client(answer)
    conn = _connection(monkeypatch, tmp_path, client)

    async def scenario() -> None:
        livestatus._scope_ctx.set(MonitoringScope("jdoe"))  # noqa: SLF001
        await conn._query_with_site("GET hosts\nColumns: name\n")  # noqa: SLF001

    asyncio.run(scenario())

    assert client.headers == ["AuthUser: jdoe\n"]


class _Remote:
    """A federated connection whose sites answer once ``answer`` is set."""

    def __init__(
        self,
        answer: threading.Event | None,
        asked: threading.Event,
        dead_sites: Iterator[Mapping[str, object]] | None = None,
    ) -> None:
        self._answer = answer
        self._asked = asked
        self._dead_sites = itertools.repeat({}) if dead_sites is None else dead_sites
        self.connections: list[object] = []
        self.deadsites: dict[str, object] = {}

    def set_only_sites(self, _sites: object) -> None: ...

    def query(self, _query: object, add_headers: str = "") -> list[object]:  # noqa: ARG002
        self._asked.set()
        if self._answer is not None:
            self._answer.wait()
        return []

    def dead_sites(self) -> Mapping[str, object]:
        return next(self._dead_sites)

    def disconnect(self) -> None: ...


def _federated(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, remotes: Iterator[_Remote]
) -> tuple[livestatus.LivestatusConnection, list[_Remote]]:
    monkeypatch.setattr(settings, "checkmk_omd_root", str(tmp_path))
    monkeypatch.setattr(settings, "connection_query_timeout", 1)
    monkeypatch.setattr(checkmk_sites, "sites_mk_mtime", lambda: 1.0)
    monkeypatch.setattr(checkmk_sites, "load_sites", lambda: {"central": {}, "remote1": {}})
    conn = livestatus.LivestatusConnection(
        socket_path=str(tmp_path / "tmp" / "run" / "live"), host=None
    )
    built: list[_Remote] = []

    def _connect(_sites: object) -> _Remote:
        built.append(remote := next(remotes))
        return remote

    monkeypatch.setattr(conn, "_new_multisite_connection", _connect)
    return conn, built


_QUERY = "GET hosts\nColumns: name\n"


def test_a_slow_remote_site_holds_up_no_other_query(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, answer: threading.Event
) -> None:
    asked = threading.Event()
    conn, _built = _federated(
        monkeypatch, tmp_path, iter([_Remote(answer, asked), _Remote(None, threading.Event())])
    )

    async def scenario() -> list[object]:
        slow = asyncio.create_task(conn._query_with_site(_QUERY))  # noqa: SLF001
        await asyncio.to_thread(asked.wait, 1)
        fast = await conn._query_with_site(_QUERY)  # noqa: SLF001
        answer.set()
        await slow
        return list(fast)

    assert asyncio.run(scenario()) == []


def test_a_connection_busy_while_a_site_recovers_does_not_mark_it_dead_again(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, answer: threading.Event
) -> None:
    asked = threading.Event()
    dead = {"remote1": {"exception": "timed out"}}
    conn, _built = _federated(
        monkeypatch,
        tmp_path,
        iter(
            [
                _Remote(answer, asked, itertools.repeat(dead)),
                _Remote(None, threading.Event(), itertools.chain([dead], itertools.repeat({}))),
            ]
        ),
    )

    async def scenario() -> list[str]:
        slow = asyncio.create_task(conn._query_with_site(_QUERY))  # noqa: SLF001
        await asyncio.to_thread(asked.wait, 1)
        await conn._query_with_site(_QUERY)  # noqa: SLF001
        seen_dead = conn.dead_sites()
        await conn._query_with_site(_QUERY)  # noqa: SLF001
        answer.set()
        await slow
        return seen_dead

    assert asyncio.run(scenario()) == ["remote1"]
    assert conn.dead_sites() == []


def test_the_federated_connections_are_bounded(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, answer: threading.Event
) -> None:
    monkeypatch.setattr(settings, "multisite_connections", 2)
    conn, built = _federated(
        monkeypatch,
        tmp_path,
        (_Remote(answer, threading.Event()) for _ in itertools.count()),
    )

    async def scenario() -> list[object]:
        return await asyncio.gather(
            *(conn._query_with_site(_QUERY) for _ in range(3)),  # noqa: SLF001
            return_exceptions=True,
        )

    results = asyncio.run(scenario())

    assert [type(r) for r in results] == [QueryTimeoutError] * 3
    assert len(built) == 2
