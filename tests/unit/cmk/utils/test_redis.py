#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.redis import disable_redis, get_redis_client, redis_enabled


class TestCheckmkRedisClient:
    def test_initialization_decode_activated(self) -> None:
        assert get_redis_client().connection_pool.connection_kwargs.get(
            "decode_responses",
            False,
        )


def test_get_redis_client_raises_when_disabled():
    with disable_redis(), pytest.raises(RuntimeError):
        get_redis_client()


def test_redis_enabled_by_default() -> None:
    assert redis_enabled()


def test_disable_redis():
    with disable_redis():
        assert not redis_enabled()
    assert redis_enabled()


def test_disable_redis_exception_handling():
    with disable_redis(), pytest.raises(Exception):
        raise Exception
    assert redis_enabled()
