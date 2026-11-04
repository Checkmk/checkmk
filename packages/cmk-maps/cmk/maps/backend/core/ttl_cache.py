#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""A small time-to-live cache with bounded eviction of the least recently set entry.

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
that need single-flight semantics fetch through
:class:`~cmk.maps.backend.core.single_flight.SingleFlight`.
"""

import time
from collections.abc import Callable


class TtlCache[K, V]:
    """A ``key -> value`` cache whose entries expire after a per-get TTL and
    whose size is bounded by evicting the entry set longest ago."""

    def __init__(
        self,
        *,
        maxsize: int = 32,
        weigh: Callable[[V], int] | None = None,
        maxweight: int | None = None,
        expire_after: float | None = None,
    ) -> None:
        """``weigh``/``maxweight`` also bound what the entries hold together, for
        values of very different size. ``expire_after`` drops entries no ``get``
        would return any more on every ``set``, so keys that are never asked
        again do not stay until they are evicted."""
        self._store: dict[K, tuple[float, V]] = {}
        self._maxsize = maxsize
        self._weigh = weigh
        self._maxweight = maxweight
        self._weight = 0
        self._expire_after = expire_after

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
        """Store ``value`` under ``key``, evicting the entry set longest ago when
        a *new* key would exceed ``maxsize``. Setting a key again makes it the
        newest, so a key kept fresh is never the one evicted."""
        now = time.monotonic() if now is None else now
        # Entries are in the order they were set, so the expired ones lead.
        while self._expire_after is not None and self._store:
            oldest = next(iter(self._store))
            if now - self._store[oldest][0] < self._expire_after:
                break
            self._drop(oldest)
        if not self._drop(key) and len(self._store) >= self._maxsize:
            self._drop(next(iter(self._store)))
        self._store[key] = (now, value)
        if self._weigh is not None:
            self._weight += self._weigh(value)
            while self._maxweight is not None and self._weight > self._maxweight:
                oldest = next(iter(self._store))
                if oldest == key:
                    break
                self._drop(oldest)

    def pop(self, key: K) -> None:
        """Drop one entry if present (no error when absent)."""
        self._drop(key)

    def invalidate(self, predicate: Callable[[K], bool] | None = None) -> None:
        """Drop every entry (``predicate`` is ``None``) or those whose key matches."""
        for key in [k for k in self._store if predicate is None or predicate(k)]:
            self._drop(key)

    def _drop(self, key: K) -> bool:
        entry = self._store.pop(key, None)
        if entry is None:
            return False
        if self._weigh is not None:
            self._weight -= self._weigh(entry[1])
        return True

    def __contains__(self, key: object) -> bool:
        return key in self._store

    def __len__(self) -> int:
        return len(self._store)
