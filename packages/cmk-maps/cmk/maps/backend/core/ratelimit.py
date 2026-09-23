#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Simple in-memory rate limiter (no external dependencies)."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock


class RateLimiter:
    """Sliding-window rate limiter keyed by arbitrary string (e.g. user name).

    Thread-safe; suitable for single-process deployments.
    """

    def __init__(self, max_calls: int, window_seconds: float) -> None:
        self._max = max_calls
        self._window = window_seconds
        self._calls: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def _prune_key(self, key: str, cutoff: float) -> deque[float] | None:
        """Drop timestamps older than cutoff; evict the key entirely when empty.

        Must be called under self._lock. Returns the still-populated deque, or
        None if the key has been evicted — preventing the _calls dict from
        growing unbounded for bursty one-off sources (NAT-masked clients,
        scanners, etc.).
        """
        q = self._calls.get(key)
        if q is None:
            return None
        while q and q[0] < cutoff:
            q.popleft()
        if not q:
            del self._calls[key]
            return None
        return q

    def is_blocked(self, key: str) -> bool:
        """Return True if the key has exceeded the limit (check only, does not record)."""
        now = time.monotonic()
        with self._lock:
            q = self._prune_key(key, now - self._window)
            return q is not None and len(q) >= self._max

    def record(self, key: str) -> None:
        """Record one attempt for key, counting it toward the sliding-window limit."""
        now = time.monotonic()
        with self._lock:
            self._prune_key(key, now - self._window)
            self._calls[key].append(now)

    def retry_after(self, key: str) -> float:
        """Seconds until the oldest recorded attempt falls outside the window."""
        now = time.monotonic()
        with self._lock:
            q = self._prune_key(key, now - self._window)
            if q is None:
                return 0.0
            return max(0.0, q[0] + self._window - now)


# 30 stream handshakes per minute per authenticated user — covers typical
# reconnect storms (tab restore, laptop wake, hidden tabs resuming) but blocks
# scripted connection floods.
ws_connect_limiter = RateLimiter(max_calls=30, window_seconds=60)

# Per-authenticated-user budget for the expensive Livestatus readers (topology,
# metric-history, object-details, folder search/host-services, map states).
# Keyed by the ticket identity, so one user's flood can't lock out another. 240/min
# (4/s sustained) is far above any real UI's paint+hover+search cadence and only
# trips on a scripted load loop driving repeated full-topology / bulk fetches.
rest_read_limiter = RateLimiter(max_calls=240, window_seconds=60)
