#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import asyncio
import contextlib

import pytest

from cmk.maps.backend.core.single_flight import SingleFlight


class _Fetch:
    def __init__(self) -> None:
        self.runs = 0
        self.release = asyncio.Event()
        self.error: Exception | None = None

    async def __call__(self) -> int:
        self.runs += 1
        run = self.runs
        await self.release.wait()
        if self.error is not None:
            raise self.error
        return run


async def _started(flights: SingleFlight[str, int], fetch: _Fetch) -> asyncio.Task[int]:
    task = asyncio.ensure_future(flights.run("k", fetch))
    await asyncio.sleep(0)
    return task


def test_callers_that_arrive_while_a_fetch_runs_get_its_result() -> None:
    async def _run() -> list[int]:
        flights: SingleFlight[str, int] = SingleFlight()
        fetch = _Fetch()
        first = await _started(flights, fetch)
        second = await _started(flights, fetch)
        fetch.release.set()
        return [await first, await second, fetch.runs]

    assert asyncio.run(_run()) == [1, 1, 1]


def test_a_caller_after_the_fetch_ended_fetches_again() -> None:
    async def _run() -> list[int]:
        flights: SingleFlight[str, int] = SingleFlight()
        fetch = _Fetch()
        fetch.release.set()
        return [await flights.run("k", fetch), await flights.run("k", fetch)]

    assert asyncio.run(_run()) == [1, 2]


def test_callers_that_arrive_while_a_fetch_runs_get_its_error() -> None:
    async def _run() -> int:
        flights: SingleFlight[str, int] = SingleFlight()
        fetch = _Fetch()
        fetch.error = RuntimeError("Livestatus went away")
        first = await _started(flights, fetch)
        second = await _started(flights, fetch)
        fetch.release.set()
        for caller in (first, second):
            with pytest.raises(RuntimeError):
                await caller
        return fetch.runs

    assert asyncio.run(_run()) == 1


def test_a_cancelled_caller_leaves_the_fetch_to_the_others() -> None:
    async def _run() -> int:
        flights: SingleFlight[str, int] = SingleFlight()
        fetch = _Fetch()
        first = await _started(flights, fetch)
        second = await _started(flights, fetch)
        first.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await first
        fetch.release.set()
        return await second

    assert asyncio.run(_run()) == 1
