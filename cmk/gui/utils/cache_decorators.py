#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.caching_redis import CacheDecorator, RedisFactory, ttl_memoize

from cmk.gui.hooks import scoped_memoize


def user_host_memoize(ttl: int, connection_factory: RedisFactory) -> CacheDecorator:
    """Cache the decorated function for some specified time in Redis.

    Args:
        ttl:
            The time-to-live for the cache in seconds.

        connection_factory:
            A function which returns a Redis instance.

    Returns:
        A decorator, which takes a function as its single parameter.

    """
    return scoped_memoize(
        clear_events=[
            "all-hosts-changed",
            "pre-activate-changes",
            "contactgroups-saved",
            "hosts-changed",
            "roles-saved",
            "users-saved",
        ],
        cache_impl=ttl_memoize,
        cache_impl_args=(),
        cache_impl_kwargs={
            "ttl": ttl,
            "connection_factory": connection_factory,
        },
    )
