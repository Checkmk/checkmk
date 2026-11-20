#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
import time
from collections.abc import Callable, Generator
from unittest.mock import MagicMock, Mock

import pytest
import redis
from fakeredis import FakeRedis
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import RedisError
from redis.exceptions import TimeoutError as RedisTimeoutError

from cmk.automations.helper._cache import Cache, CacheError


@pytest.fixture(name="cache")
def get_cache() -> Generator[Cache]:
    cache = Cache.setup(client=FakeRedis())
    yield cache


def test_set_and_get_last_change_detected(cache: Cache) -> None:
    now = time.time()
    cache.store_last_detected_change(now)
    assert cache.get_last_detected_change() == now


def test_get_last_change_detected_unset(cache: Cache) -> None:
    assert cache.get_last_detected_change() == 0.0


def test_get_changes_unwatched_unset(cache: Cache) -> None:
    assert cache.get_changes_unwatched() is None


def test_reload_required(cache: Cache) -> None:
    cache.store_last_detected_change(1.0)
    assert cache.reload_required(0.0)


def test_reload_required_after_the_last_reload_while_changes_are_unwatched(cache: Cache) -> None:
    cache.store_last_detected_change(1.0)
    cache.store_changes_unwatched(unwatched=True)

    assert cache.reload_required(2.0)


def test_reload_required_while_it_is_unknown_whether_changes_are_unwatched(cache: Cache) -> None:
    """As after a restart of Redis, which keeps nothing on disk, until the watcher restores it."""
    assert cache.reload_required(time.time())


@pytest.mark.parametrize(
    "error",
    [
        pytest.param(RedisConnectionError(), id="unavailable"),
        pytest.param(RedisTimeoutError("Timeout reading from socket"), id="timeout"),
    ],
)
def test_reload_required_returns_true_on_cache_error(cache: Cache, error: RedisError) -> None:
    """When Redis fails, reload_required must return True (force reload) instead of raising."""
    broken_client = MagicMock()
    broken_client.get.side_effect = error
    failing_cache = dataclasses.replace(cache, _client=broken_client)
    assert failing_cache.reload_required(0.0) is True


@pytest.mark.parametrize(
    "access",
    [
        pytest.param(lambda cache: cache.store_last_detected_change(1.0), id="store change"),
        pytest.param(lambda cache: cache.get_last_detected_change(), id="get change"),
        pytest.param(
            lambda cache: cache.store_changes_unwatched(unwatched=True), id="store unwatched"
        ),
        pytest.param(lambda cache: cache.get_changes_unwatched(), id="get unwatched"),
    ],
)
def test_redis_timeout_raises_cache_error(access: Callable[[Cache], object]) -> None:
    client = Mock(spec=redis.Redis)
    client.set.side_effect = client.get.side_effect = RedisTimeoutError(
        "Timeout reading from socket"
    )

    with pytest.raises(CacheError):
        access(Cache.setup(client=client))
