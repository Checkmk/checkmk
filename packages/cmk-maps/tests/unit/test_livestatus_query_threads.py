#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import asyncio
import threading
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from cmk.maps.backend.connections import livestatus
from cmk.maps.backend.connections.base import QueryTimeoutError
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


def test_the_user_reaches_the_query_thread(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, answer: threading.Event
) -> None:
    answer.set()
    client = _Client(answer)
    conn = _connection(monkeypatch, tmp_path, client)

    async def scenario() -> None:
        livestatus._auth_user_ctx.set("jdoe")  # noqa: SLF001
        await conn._query_with_site("GET hosts\nColumns: name\n")  # noqa: SLF001

    asyncio.run(scenario())

    assert client.headers == ["AuthUser: jdoe\n"]
