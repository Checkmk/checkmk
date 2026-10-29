#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Keeps the calls of one agent run within the rate limits Prism Central reports

Prism Central limits every endpoint separately (x-api-ratelimit-*, e.g. 10 calls per second
for the stats of storage containers) and all calls together (x-ratelimit-*, 30 to 80 per
second depending on its size). The limits come with every response, so the first call to an
endpoint goes alone and tells the others how fast they may follow.
"""

import re
import threading
import time
from collections import deque
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

# Calls for different entities count against one limit
_EXT_ID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE)
ALL_ENDPOINTS = "*"
# Prism Central doesn't report the window of its overall limit, the documentation says per second
OVERALL_PERIOD = 1.0
# How often a call checks again whether the first call to its endpoint has come back
PROBE_POLL = 0.05


def endpoint_of(url: str) -> str:
    return _EXT_ID.sub("{extId}", url.split("?", 1)[0])


@dataclass
class _Window:
    limit: int | None = None
    period: float = OVERALL_PERIOD
    known: bool = False
    probing: bool = False
    blocked_until: float = 0.0
    sent: deque[float] = field(default_factory=deque)

    def delay(self, now: float) -> float:
        """How long a call has to wait before it may be sent, 0 if it may go now"""
        if self.blocked_until > now:
            return self.blocked_until - now
        if not self.known:
            return PROBE_POLL if self.probing else 0.0
        if self.limit is None:
            return 0.0
        while self.sent and self.sent[0] <= now - self.period:
            self.sent.popleft()
        return 0.0 if len(self.sent) < self.limit else self.sent[0] + self.period - now

    def record(self, now: float) -> None:
        if not self.known:
            self.probing = True
        elif self.limit is None:
            # Nothing to count against
            return
        self.sent.append(now)

    def learn(
        self, limit: int | None, period: float, remaining: int | None, now: float, succeeded: bool
    ) -> None:
        if limit is None and not succeeded:
            # An error page says nothing about the limits, the next call has to find out
            self.probing = False
            return
        if limit == 0:
            # Nothing allowed for now: after a window, one call finds out the limit again
            self.limit, self.period, self.known, self.probing = None, period, False, False
            self.blocked_until = now + period
            return
        # A response without limits, e.g. a 401 before the cookies are renewed, doesn't lift
        # the limits learned before
        if limit is not None or not self.known:
            self.limit, self.period = limit, period
        if self.limit is None:
            self.sent.clear()
        self.known, self.probing = True, False
        # Other clients of Prism Central count too: none left means none left
        if remaining == 0:
            self.blocked_until = now + period


def _period(headers: Mapping[str, str]) -> float:
    try:
        period = float(headers["x-api-ratelimit-refresh-period-seconds"])
    except KeyError, ValueError:
        return OVERALL_PERIOD
    return period if period > 0 else OVERALL_PERIOD


def _int(headers: Mapping[str, str], name: str) -> int | None:
    try:
        return int(headers[name])
    except KeyError, ValueError:
        return None


class RateLimits:
    """Shared by all threads of one agent run"""

    def __init__(
        self,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._clock = clock
        self._sleep = sleep
        self._lock = threading.Lock()
        self._windows: dict[str, _Window] = {}

    def acquire(self, endpoint: str, deadline: float) -> bool:
        """Wait until a call to the endpoint may be sent. False, without waiting, if that would
        be after the deadline: the limits come from Prism Central and may be long."""
        while (delay := self.reserve(endpoint)) > 0:
            if self._clock() + delay >= deadline:
                return False
            self._sleep(delay)
        return True

    def reserve(self, endpoint: str) -> float:
        """Count a call to the endpoint and return 0, or return how long to wait first"""
        with self._lock:
            now = self._clock()
            windows = [self._window(endpoint), self._window(ALL_ENDPOINTS)]
            if (delay := max(window.delay(now) for window in windows)) > 0:
                return delay
            for window in windows:
                window.record(now)
            return 0.0

    def update(self, endpoint: str, headers: Mapping[str, str], succeeded: bool = True) -> None:
        """Learn the limits from a response; a successful one without them means no limits"""
        with self._lock:
            now = self._clock()
            self._window(endpoint).learn(
                _int(headers, "x-api-ratelimit-limit"),
                _period(headers),
                _int(headers, "x-api-ratelimit-remaining"),
                now,
                succeeded,
            )
            self._window(ALL_ENDPOINTS).learn(
                _int(headers, "x-ratelimit-limit"),
                OVERALL_PERIOD,
                _int(headers, "x-ratelimit-remaining"),
                now,
                succeeded,
            )

    def back_off(self, endpoint: str, seconds: float | None) -> None:
        """Prism Central refused a call (429): no call to the endpoint goes before it may be
        retried, after Retry-After or else one window"""
        with self._lock:
            window = self._window(endpoint)
            until = self._clock() + (window.period if seconds is None else seconds)
            window.blocked_until = max(window.blocked_until, until)

    def release(self, endpoint: str) -> None:
        """A call got no response: let the next one find out the limits"""
        with self._lock:
            for name in (endpoint, ALL_ENDPOINTS):
                if not (window := self._window(name)).known:
                    window.probing = False

    def _window(self, endpoint: str) -> _Window:
        return self._windows.setdefault(endpoint, _Window())
