#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Simple in-memory rate limiter (no external dependencies)."""

import functools
import re
import time
from collections import defaultdict, deque
from collections.abc import Callable
from pathlib import Path
from threading import Lock

from cmk.maps.backend.core.config import settings


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

    def refund(self, key: str) -> None:
        """Take back the latest attempt recorded for key."""
        with self._lock:
            if q := self._calls.get(key):
                q.pop()
                if not q:
                    del self._calls[key]

    def retry_after(self, key: str) -> float:
        """Seconds until the oldest recorded attempt falls outside the window."""
        now = time.monotonic()
        with self._lock:
            q = self._prune_key(key, now - self._window)
            if q is None:
                return 0.0
            return max(0.0, q[0] + self._window - now)


class ConcurrencyLimiter:
    """Caps how many resources are held at once, per key and site-wide.

    Thread-safe; suitable for single-process deployments. Where RateLimiter caps
    the *rate* of new acquisitions, this caps how many are *held simultaneously*.
    """

    def __init__(self, max_per_key: int, max_total: int | Callable[[], int]) -> None:
        self._max_per_key = max_per_key
        self._max_total = max_total
        self._counts: dict[str, int] = {}
        self._total = 0
        self._lock = Lock()

    def try_acquire(self, key: str) -> bool:
        """Reserve one slot for key; return False (reserving nothing) when full."""
        max_total = self._max_total() if callable(self._max_total) else self._max_total
        with self._lock:
            held = self._counts.get(key, 0)
            if self._total >= max_total or held >= self._max_per_key:
                return False
            self._counts[key] = held + 1
            self._total += 1
            return True

    def release(self, key: str) -> None:
        """Give back one slot previously acquired for key (idempotent at zero)."""
        with self._lock:
            held = self._counts.get(key, 0)
            if held <= 0:
                return
            if held == 1:
                del self._counts[key]
            else:
                self._counts[key] = held - 1
            self._total -= 1


# 30 stream handshakes per minute per authenticated user — covers typical
# reconnect storms (tab restore, laptop wake, hidden tabs resuming) but blocks
# scripted connection floods.
ws_connect_limiter = RateLimiter(max_calls=30, window_seconds=60)

# Setup's Apache process tuning writes both into etc/apache/conf.d/zzz_check_mk.conf.
_MAX_CLIENTS_RE = re.compile(
    r"^[ \t]*(?:MaxClients|MaxRequestWorkers)[ \t]+(\d+)[ \t]*$", re.I | re.M
)
_SERVER_LIMIT_RE = re.compile(r"^[ \t]*ServerLimit[ \t]+(\d+)[ \t]*$", re.I | re.M)


def site_stream_limit(apache_dir: Path | None = None) -> int:
    """How many streams the site holds at once: an eighth of its Apache workers.

    A worker holding a stream keeps the memory of a GUI process, so the maps shown
    beyond it poll their states, which the daemon fetches once per interval for
    all viewers who see the same.
    """
    apache_dir = apache_dir or Path(settings.checkmk_omd_root) / "etc" / "apache"
    files = [apache_dir / "apache.conf", *sorted((apache_dir / "conf.d").glob("*.conf"))]
    workers = _apache_workers(tuple((f, mtime) for f in files if (mtime := _mtime(f)) is not None))
    return max(workers // 8, 1)


def _mtime(path: Path) -> int | None:
    try:
        return path.stat().st_mtime_ns
    except OSError:
        return None


@functools.lru_cache(maxsize=1)
def _apache_workers(stamp: tuple[tuple[Path, int], ...]) -> int:
    """The worker processes Apache runs, from the last value it reads of each directive."""
    max_clients, server_limit = 64, None
    for path, _ in stamp:
        try:
            text = path.read_text(errors="replace")
        except OSError:
            continue
        if values := _MAX_CLIENTS_RE.findall(text):
            max_clients = int(values[-1])
        if values := _SERVER_LIMIT_RE.findall(text):
            server_limit = int(values[-1])
    return max(min(max_clients, server_limit or max_clients), 1)


# Concurrently held SSE streams. Each stream pins one of the site Apache's
# prefork workers for as long as it is open, so the handshake rate cap above is
# not enough on its own. Two per user cover a wall and a desk (hidden tabs close
# theirs); further views of the user poll.
sse_stream_limiter = ConcurrencyLimiter(max_per_key=2, max_total=site_stream_limit)

# Per-authenticated-user budget for the expensive Livestatus readers (topology,
# metric-history, object-details, folder search/host-services, map states not
# kept for the interval). Keyed by the authenticated user, so each user has their
# own budget. 240/min (4/s sustained) is far above any real UI's paint+hover+search
# cadence.
rest_read_limiter = RateLimiter(max_calls=240, window_seconds=60)

# Per-user budget for the polls the states kept for the interval answer. They
# spare Livestatus, so it holds twenty tabs polling every second.
kept_states_limiter = RateLimiter(max_calls=1200, window_seconds=60)
