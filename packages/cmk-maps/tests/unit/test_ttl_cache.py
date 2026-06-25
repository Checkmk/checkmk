#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Unit tests for the daemon's TTL cache helper."""

from __future__ import annotations

from cmk.maps.backend.core.ttl_cache import TtlCache


def test_get_returns_value_within_ttl() -> None:
    cache: TtlCache[str, int] = TtlCache()
    cache.set("a", 1, now=100.0)
    assert cache.get("a", ttl=10.0, now=105.0) == 1


def test_get_returns_none_when_expired() -> None:
    cache: TtlCache[str, int] = TtlCache()
    cache.set("a", 1, now=100.0)
    assert cache.get("a", ttl=10.0, now=110.0) is None  # >= ttl is expired
    assert cache.get("a", ttl=10.0, now=109.9) == 1


def test_get_missing_key_is_none() -> None:
    cache: TtlCache[str, int] = TtlCache()
    assert cache.get("absent", ttl=10.0, now=0.0) is None


def test_fifo_eviction_on_new_key_over_maxsize() -> None:
    cache: TtlCache[str, int] = TtlCache(maxsize=2)
    cache.set("a", 1, now=0.0)
    cache.set("b", 2, now=0.0)
    cache.set("c", 3, now=0.0)  # evicts the oldest insertion ("a")
    assert cache.get("a", ttl=99.0, now=0.0) is None
    assert cache.get("b", ttl=99.0, now=0.0) == 2
    assert cache.get("c", ttl=99.0, now=0.0) == 3


def test_updating_existing_key_does_not_evict() -> None:
    cache: TtlCache[str, int] = TtlCache(maxsize=2)
    cache.set("a", 1, now=0.0)
    cache.set("b", 2, now=0.0)
    cache.set("a", 11, now=0.0)  # update, not a new key → no eviction
    assert cache.get("a", ttl=99.0, now=0.0) == 11
    assert cache.get("b", ttl=99.0, now=0.0) == 2
    assert len(cache) == 2


def test_pop_removes_entry_and_is_safe_when_absent() -> None:
    cache: TtlCache[str, int] = TtlCache()
    cache.set("a", 1, now=0.0)
    cache.pop("a")
    cache.pop("a")  # no error
    assert "a" not in cache


def test_invalidate_all() -> None:
    cache: TtlCache[str, int] = TtlCache()
    cache.set("a", 1, now=0.0)
    cache.set("b", 2, now=0.0)
    cache.invalidate()
    assert len(cache) == 0


def test_invalidate_by_predicate() -> None:
    cache: TtlCache[str, int] = TtlCache()
    cache.set("keep", 1, now=0.0)
    cache.set("drop", 2, now=0.0)
    cache.invalidate(lambda k: k == "drop")
    assert "drop" not in cache
    assert cache.get("keep", ttl=99.0, now=0.0) == 1
