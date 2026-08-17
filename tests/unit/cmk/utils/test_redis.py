#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import cast

import pytest
from redis import ConnectionError as RedisConnectionError
from redis import Redis
from redis import TimeoutError as RedisTimeoutError

from cmk.utils.redis import (
    disable_redis,
    get_redis_client,
    redis_enabled,
    redis_server_reachable,
)


class TestCheckmkRedisClient:
    def test_initialization_decode_activated(self) -> None:
        assert get_redis_client().connection_pool.connection_kwargs.get(
            "decode_responses",
            False,
        )


def test_get_redis_client_raises_when_disabled() -> None:
    with disable_redis(), pytest.raises(RuntimeError):
        get_redis_client()


def test_redis_enabled_by_default() -> None:
    assert redis_enabled()


def test_disable_redis() -> None:
    with disable_redis():
        assert not redis_enabled()
    assert redis_enabled()


def test_disable_redis_exception_handling() -> None:
    with disable_redis(), pytest.raises(ValueError):
        raise ValueError
    assert redis_enabled()


class _PingingClient:
    def __init__(self, error: Exception | None) -> None:
        self._error = error

    def ping(self) -> bool:
        if self._error is not None:
            raise self._error
        return True


def test_redis_server_reachable() -> None:
    assert redis_server_reachable(cast(Redis, _PingingClient(None)))


@pytest.mark.parametrize(
    "error",
    [
        pytest.param(RedisConnectionError("No such file or directory"), id="connection_error"),
        # Redis is single threaded: a client blocking it makes the ping run
        # into redis-py's socket timeout.
        pytest.param(RedisTimeoutError("Timeout reading from socket"), id="timeout_error"),
    ],
)
def test_redis_server_not_reachable(error: Exception) -> None:
    assert not redis_server_reachable(cast(Redis, _PingingClient(error)))
