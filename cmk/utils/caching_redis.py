#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Redis backed cache decorators

Currently available:

 * ttl_cache

"""

from __future__ import annotations

import functools
import hashlib
import marshal
import typing
from collections.abc import Callable

from redis.exceptions import RedisError

from cmk.utils.redis import redis_enabled

if typing.TYPE_CHECKING:
    # There is a redis module in this package, making it hard to doctest.
    import redis

P = typing.ParamSpec("P")
R = typing.TypeVar("R")
F = typing.TypeVar("F")
RedisFactory = Callable[[], "redis.Redis[str]"]
CacheWrapper = Callable[P, R]
CacheDecorator = Callable[[F], CacheWrapper[P, R]]


def ttl_memoize(ttl: int, connection_factory: RedisFactory) -> CacheDecorator:
    """Decorator factory for caching function results in Redis with a TTL.

    This decorator does nothing to ensure no duplicate calculations will ever be done. If multiple
    re-builds are asked for at the same time, all of these re-build will be done.

    The invalidation of the cache is done by Redis itself. If the key times out, the cache
    is gone. If multiple processes rebuild one entry at the same time, all of them will be written
    sequentially onto the same key. As Redis does not consider this a conflict, all is fine.

    Limitations:
        It should only be used for primitive types (numbers, strings, list, dict, etc.) as
        *parameters* but not whole classes, which can vary in their repr() evaluation. The result
        may be more involved, but not the parameters.

    Args:
        ttl: Time to live for cache entries, in seconds.
        connection_factory: Callable that returns a Redis connection.

    """
    encode, decode = marshal.dumps, marshal.loads

    def decorator(func):
        func_name = _get_dotted_path(func)
        prefix = f"redis_cache:{func_name}"

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if redis_enabled():
                try:
                    conn = connection_factory()
                    key = hashed_cache_key(sorted_cache_key(*args, **kwargs))
                    cache_key = f"{prefix}:{key}"

                    # ensure_bytes:
                    # Not sure why in the tests, sometimes we get a <str> and sometimes we get <bytes>
                    cached_result = ensure_bytes(conn.get(cache_key))
                    if cached_result is not None:
                        return decode(cached_result)
                    result = func(*args, **kwargs)
                    conn.set(cache_key, encode(result), ex=ttl)
                    return result
                except (RuntimeError, RedisError):
                    pass

            return func(*args, **kwargs)

        def cache_clear(*_args: object) -> None:
            if redis_enabled():
                # Note: Do not catch any exceptions
                # If there is an error, the developer should see it
                conn = connection_factory()
                for key in conn.scan_iter(prefix + "*"):
                    conn.delete(key)

        # Tried very hard to make the types work here as well, but to no avail.
        wrapper.cache_clear = cache_clear  # type: ignore[attr-defined]

        return wrapper

    return decorator


def hashed_cache_key(arg_tuple: tuple[object, ...]) -> str:
    """Build a string hash from a tuple.

    Examples:
        >>> hashed_cache_key(sorted_cache_key(1, 2, 3, four=4))
        '010389fa0699173ddcaf0b99ee4d974f43a36f7d'

        >>> hashed_cache_key(sorted_cache_key(1.0, 2.0, 3.0, four=4))
        'c327161146022eefe9ce2a7ef11e099e6a37fc8c'

    """
    return hashlib.sha1(repr(arg_tuple).encode(), usedforsecurity=False).hexdigest()


def sorted_cache_key(*args: object, **kwargs: object) -> tuple[object, ...]:
    """Build tuple from arguments and sorted keyword arguments.

    Examples:
        >>> sorted_cache_key("1", "2", three="3", four="4")
        ('1', '2', 'four', '4', 'three', '3')

        >>> sorted_cache_key("1", "2", "3", four="4")
        ('1', '2', '3', 'four', '4')

    """
    if kwargs:
        return args + sum(sorted(kwargs.items()), ())

    return args


def _get_dotted_path(callable_obj: Callable[P, R]) -> str:
    """Derive something like a dotted path to the object being passed.

    The resulting path is not actually usable for imports or any other purpose. It is used
    solely for putting an "identity" on the passed object. If a name can't be derived, an id()
    will be used instead. This holds until the process is restarted of course, so even caching
    over a long time (over process boundaries) can't be done reliably with this path.

    Examples:
        >>> l = lambda: 1
        >>> _get_dotted_path(l) == _get_dotted_path(l)
        True

    Args:
        callable_obj:
            Some Python object. Can be a function, a class or any other thing.

    Returns:
        The "dotte path".

    """
    module = getattr(callable_obj, "__module__", "unknown")
    qualname = getattr(
        callable_obj,
        "__qualname__",
        getattr(callable_obj, "__name__", str(id(callable_obj))),
    )
    if qualname == "<lambda>":
        qualname = str(id(callable_obj))
    return f"{module}.{qualname}"


def ensure_bytes(
    inp: bytes | str | None,
    errors: typing.Literal["strict", "ignore", "replace"] = "strict",
) -> bytes | None:
    if inp is None:
        return None
    if isinstance(inp, bytes):
        return inp
    if isinstance(inp, str):
        return inp.encode(errors=errors)
    raise ValueError(f"Not a valid type {type(inp)}.")


# Example usage:
# Some redis cache decorator, which can be used throughout the multiple apache processes
# def user_host_memoize(ttl: int, connection_factory: RedisFactory) -> CacheDecorator:
#    """Cache the decorated function for some specified time in Redis.
#
#    Args:
#        ttl:
#            The time-to-live for the cache in seconds.
#
#        connection_factory:
#            A function which returns a Redis instance.
#
#    Returns:
#        A decorator, which takes a function as its single parameter.
#
#    """
#    return scoped_memoize(
#        clear_events=[
#            "all-hosts-changed",
#            "pre-activate-changes",
#            "contactgroups-saved",
#            "hosts-changed",
#            "roles-saved",
#            "users-saved",
#        ],
#        cache_impl=ttl_memoize,
#        cache_impl_args=(),
#        cache_impl_kwargs={
#            "ttl": ttl,
#            "connection_factory": connection_factory,
#        },
#    )
#
# @user_host_memoize(1800, connection_factory=_get_redis_client)
# def _user_has_permission(mode: str, file_name: str, user_id: UserId) -> bool:
#    """Check if a user has the permission to either the mode or the page.
#    ...
#
