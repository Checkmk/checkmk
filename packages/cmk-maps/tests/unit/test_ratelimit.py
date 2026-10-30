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

import os
from collections.abc import Iterator
from pathlib import Path

import pytest

from cmk.maps.backend.core.ratelimit import (
    ConcurrencyLimiter,
    RateLimiter,
    site_stream_limit,
    sse_stream_limiter,
    ws_connect_limiter,
)


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


def test_a_refund_takes_back_an_attempt(clock: _Clock) -> None:
    limiter = RateLimiter(max_calls=2, window_seconds=60)
    for _ in range(2):
        limiter.record("k")
    limiter.refund("k")
    assert limiter.is_blocked("k") is False


def test_a_refund_without_attempts_is_a_noop(clock: _Clock) -> None:
    limiter = RateLimiter(max_calls=1, window_seconds=60)
    limiter.refund("k")
    limiter.record("k")
    assert limiter.is_blocked("k") is True


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


def test_concurrency_allows_up_to_the_per_key_limit() -> None:
    limiter = ConcurrencyLimiter(max_per_key=2, max_total=10)
    assert limiter.try_acquire("k") is True
    assert limiter.try_acquire("k") is True
    assert limiter.try_acquire("k") is False


def test_concurrency_release_frees_a_slot() -> None:
    limiter = ConcurrencyLimiter(max_per_key=1, max_total=10)
    assert limiter.try_acquire("k") is True
    assert limiter.try_acquire("k") is False
    limiter.release("k")
    assert limiter.try_acquire("k") is True


def test_concurrency_global_cap_blocks_across_keys() -> None:
    limiter = ConcurrencyLimiter(max_per_key=5, max_total=2)
    assert limiter.try_acquire("a") is True
    assert limiter.try_acquire("b") is True
    # Total budget spent even though neither key hit its own limit.
    assert limiter.try_acquire("c") is False
    limiter.release("a")
    assert limiter.try_acquire("c") is True


def test_concurrency_keys_are_independent() -> None:
    limiter = ConcurrencyLimiter(max_per_key=1, max_total=10)
    assert limiter.try_acquire("a") is True
    assert limiter.try_acquire("a") is False
    assert limiter.try_acquire("b") is True


def test_concurrency_release_at_zero_is_a_noop() -> None:
    limiter = ConcurrencyLimiter(max_per_key=1, max_total=10)
    limiter.release("never-acquired")
    # The spurious release must not hand out a negative-debt bonus slot.
    assert limiter.try_acquire("never-acquired") is True
    assert limiter.try_acquire("never-acquired") is False


def test_sse_stream_limiter_holds_two_streams_per_user() -> None:
    # The module-level limiter guarding concurrent SSE streams.
    held = 0
    try:
        while sse_stream_limiter.try_acquire("wall-display"):
            held += 1
        assert held == 2
    finally:
        for _ in range(held):
            sse_stream_limiter.release("wall-display")


def test_concurrency_global_cap_follows_a_callable() -> None:
    cap = [1]
    limiter = ConcurrencyLimiter(max_per_key=5, max_total=lambda: cap[0])
    assert limiter.try_acquire("a") is True
    assert limiter.try_acquire("b") is False
    cap[0] = 2
    assert limiter.try_acquire("b") is True


def _apache_dir(tmp_path: Path, workers: int, setup: int | None = None) -> Path:
    (tmp_path / "conf.d").mkdir(exist_ok=True)
    (tmp_path / "apache.conf").write_text(
        f"# MaxClients: maximum number of connections\nServerLimit {workers}\n"
        f"MaxClients {workers}\nInclude conf.d/*.conf\n"
    )
    if setup is not None:
        (tmp_path / "conf.d" / "zzz_check_mk.conf").write_text(
            f"ServerLimit {setup}\nMaxClients {setup}\n"
        )
    return tmp_path


def test_site_streams_take_an_eighth_of_the_default_workers(tmp_path: Path) -> None:
    assert site_stream_limit(_apache_dir(tmp_path, 64)) == 8


def test_site_streams_follow_the_workers_setup_configures(tmp_path: Path) -> None:
    assert site_stream_limit(_apache_dir(tmp_path, 64, setup=128)) == 16


def test_site_streams_keep_one_with_few_workers(tmp_path: Path) -> None:
    assert site_stream_limit(_apache_dir(tmp_path, 64, setup=4)) == 1


def test_site_streams_stay_under_the_server_limit(tmp_path: Path) -> None:
    apache_dir = _apache_dir(tmp_path, 64)
    (apache_dir / "conf.d" / "tuning.conf").write_text("MaxRequestWorkers 256\n")
    assert site_stream_limit(apache_dir) == 8


def test_site_streams_follow_a_changed_setup(tmp_path: Path) -> None:
    apache_dir = _apache_dir(tmp_path, 64, setup=128)
    assert site_stream_limit(apache_dir) == 16
    setup = apache_dir / "conf.d" / "zzz_check_mk.conf"
    setup.write_text("ServerLimit 32\nMaxClients 32\n")
    os.utime(setup, ns=(0, setup.stat().st_mtime_ns + 1_000_000))
    assert site_stream_limit(apache_dir) == 4


def test_site_streams_default_without_apache_config(tmp_path: Path) -> None:
    assert site_stream_limit(tmp_path) == 8


def test_site_streams_read_the_setup_without_the_main_config(tmp_path: Path) -> None:
    apache_dir = _apache_dir(tmp_path, 64, setup=32)
    (apache_dir / "apache.conf").unlink()
    assert site_stream_limit(apache_dir) == 4
