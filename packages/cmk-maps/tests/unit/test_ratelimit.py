#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# ruff: noqa: ARG001  # Unused fixtures are needed for setup side effects

"""Unit tests for the in-memory sliding-window rate limiter.

The limiter is the daemon's own DoS defense for the SSE handshake, so
its window arithmetic and memory pruning are pinned here rather than only
being exercised indirectly through the route.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from cmk.maps.backend.core.ratelimit import RateLimiter, ws_connect_limiter


class _Clock:
    """Deterministic replacement for ``time.monotonic``."""

    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture(name="clock")
def _clock(monkeypatch: pytest.MonkeyPatch) -> Iterator[_Clock]:
    clock = _Clock()
    # String target so mypy's implicit-reexport check does not trip on
    # ``ratelimit.time``; this patches the stdlib ``time.monotonic`` the module
    # calls (restored by monkeypatch after the test).
    monkeypatch.setattr("cmk.maps.backend.core.ratelimit.time.monotonic", clock)
    yield clock


def test_allows_calls_below_limit(clock: _Clock) -> None:
    limiter = RateLimiter(max_calls=3, window_seconds=60)
    for _ in range(2):
        limiter.record("k")
    assert limiter.is_blocked("k") is False


def test_blocks_once_limit_is_reached(clock: _Clock) -> None:
    limiter = RateLimiter(max_calls=3, window_seconds=60)
    for _ in range(3):
        limiter.record("k")
    assert limiter.is_blocked("k") is True


def test_is_blocked_does_not_record(clock: _Clock) -> None:
    limiter = RateLimiter(max_calls=1, window_seconds=60)
    # Repeated checks must not themselves fill the bucket.
    for _ in range(5):
        assert limiter.is_blocked("k") is False
    limiter.record("k")
    assert limiter.is_blocked("k") is True


def test_window_slides_and_unblocks(clock: _Clock) -> None:
    limiter = RateLimiter(max_calls=2, window_seconds=60)
    limiter.record("k")
    limiter.record("k")
    assert limiter.is_blocked("k") is True
    # Both timestamps age out of the window.
    clock.advance(61)
    assert limiter.is_blocked("k") is False


def test_window_boundary_is_exclusive(clock: _Clock) -> None:
    limiter = RateLimiter(max_calls=1, window_seconds=60)
    limiter.record("k")
    clock.advance(60)  # cutoff == recorded timestamp; strictly-older is dropped
    assert limiter.is_blocked("k") is True
    clock.advance(0.001)
    assert limiter.is_blocked("k") is False


def test_keys_are_independent(clock: _Clock) -> None:
    limiter = RateLimiter(max_calls=1, window_seconds=60)
    limiter.record("a")
    assert limiter.is_blocked("a") is True
    assert limiter.is_blocked("b") is False


def test_retry_after_counts_down(clock: _Clock) -> None:
    limiter = RateLimiter(max_calls=1, window_seconds=60)
    limiter.record("k")
    assert limiter.retry_after("k") == pytest.approx(60.0)
    clock.advance(20)
    assert limiter.retry_after("k") == pytest.approx(40.0)


def test_retry_after_unknown_key_is_zero(clock: _Clock) -> None:
    limiter = RateLimiter(max_calls=1, window_seconds=60)
    assert limiter.retry_after("never-seen") == 0.0


def test_pruning_evicts_empty_keys(clock: _Clock) -> None:
    limiter = RateLimiter(max_calls=5, window_seconds=60)
    limiter.record("bursty")
    assert "bursty" in limiter._calls  # noqa: SLF001
    clock.advance(61)
    # Any window-aware operation must drop the now-empty deque so the dict does
    # not grow unbounded for one-off sources (scanners, NAT-masked clients).
    limiter.is_blocked("bursty")
    assert "bursty" not in limiter._calls  # noqa: SLF001


def test_ws_connect_limiter_is_thirty_per_minute(clock: _Clock) -> None:
    # The module-level limiter guarding the SSE handshake.
    assert ws_connect_limiter._max == 30  # noqa: SLF001
    assert ws_connect_limiter._window == 60  # noqa: SLF001
