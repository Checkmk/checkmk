#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import collections
import time

import pytest
from fakeredis import FakeRedis

from cmk.utils.caching_redis import ttl_memoize


@pytest.fixture(name="cached_function")
def cached_function_fixture():
    # NOTE: With no parameters, FakeRedis() will return a fresh instance every
    # time! For details, see https://github.com/cunla/fakeredis-py/pull/303
    @ttl_memoize(10, lambda: FakeRedis(host="localhost"))
    def time_based_function(param: int) -> float:
        return time.time() * param

    return time_based_function


def test_redis_caching_decorator(cached_function):
    # TODO: test expiry
    results = collections.defaultdict(set)
    for index in range(1, 10):
        results[index].add(cached_function(index))
        results[index].add(cached_function(index))

    prev = None
    for index in range(1, 10):
        entry = results[index]
        assert len(entry) == 1
        assert entry != prev

    # We ensure that multiple runs won't generate different times.
    for result in results.values():
        assert len(result) == 1

    cached_function.cache_clear()

    for index in range(1, 10):
        entry = results[index]
        assert entry != {cached_function(index)}
