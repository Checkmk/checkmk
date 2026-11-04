#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""One run of a fetch for everyone who asks for it while it is under way."""

import asyncio
from collections.abc import Awaitable, Callable


class SingleFlight[K, V]:
    """Hands the callers that arrive while a fetch for their key runs its
    result or its error, instead of fetching again."""

    def __init__(self) -> None:
        self._flights: dict[K, asyncio.Future[V]] = {}

    async def run(self, key: K, fetch: Callable[[], Awaitable[V]]) -> V:
        """A caller that is cancelled leaves the fetch running for the others."""
        if (flight := self._flights.get(key)) is None:
            flight = asyncio.ensure_future(fetch())
            self._flights[key] = flight
            flight.add_done_callback(lambda done: self._land(key, done))
        return await asyncio.shield(flight)

    def _land(self, key: K, done: asyncio.Future[V]) -> None:
        del self._flights[key]
        if not done.cancelled():
            # Its callers got the error; with none left asyncio would log it.
            done.exception()
