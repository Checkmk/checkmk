#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""A small time-to-live cache with bounded, insertion-order (FIFO) eviction.

Several daemon hot paths cache an expensive Livestatus result for a few seconds
so concurrent refreshes of the same map (multi-tab, multi-user) share one
round-trip. They all want the same three things: expire an entry after a TTL,
bound the map to a fixed size, and (for module-level caches) drop entries
selectively on invalidation. This collects that into one tested helper instead
of re-deriving the ``(timestamp, value)`` bookkeeping at each call site.

The TTL is passed per :meth:`get`, not fixed at construction, so a caller whose
TTL comes from a live setting stays correct without rebuilding the cache. Time
is ``time.monotonic()`` (never wall-clock, so it is immune to clock steps);
``now`` is injectable for tests. Not thread-safe and not async-locked — callers
that need single-flight semantics wrap :meth:`get`/:meth:`set` in their own lock.
"""

from __future__ import annotations

import time
from collections.abc import Callable


class TtlCache[K, V]:
    """A ``key -> value`` cache whose entries expire after a per-get TTL and
    whose size is bounded by FIFO eviction of the oldest insertion."""

    def __init__(self, *, maxsize: int = 32) -> None:
        self._store: dict[K, tuple[float, V]] = {}
        self._maxsize = maxsize

    def get(self, key: K, *, ttl: float, now: float | None = None) -> V | None:
        """Return the cached value, or ``None`` if absent or older than ``ttl``."""
        entry = self._store.get(key)
        if entry is None:
            return None
        stored_at, value = entry
        if (time.monotonic() if now is None else now) - stored_at >= ttl:
            return None
        return value

    def set(self, key: K, value: V, *, now: float | None = None) -> None:
        """Store ``value`` under ``key``, evicting the oldest entry first when a
        *new* key would exceed ``maxsize`` (updating an existing key never evicts)."""
        if key not in self._store and len(self._store) >= self._maxsize:
            self._store.pop(next(iter(self._store)))
        self._store[key] = (time.monotonic() if now is None else now, value)

    def pop(self, key: K) -> None:
        """Drop one entry if present (no error when absent)."""
        self._store.pop(key, None)

    def invalidate(self, predicate: Callable[[K], bool] | None = None) -> None:
        """Drop every entry (``predicate`` is ``None``) or those whose key matches."""
        for key in [k for k in self._store if predicate is None or predicate(k)]:
            self._store.pop(key, None)

    def __contains__(self, key: object) -> bool:
        return key in self._store

    def __len__(self) -> int:
        return len(self._store)
