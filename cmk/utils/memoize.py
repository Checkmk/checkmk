#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""A helper module providing simple caching mechanism (without invalidation).
It provides a decorator that can be used to cache function results based on the
given function arguments."""

from typing import Any, Callable, Dict, Set, Tuple, Type, Union

# The functions that violate this checker are borrowed from official python
# code and are done for performance reasons.
# pylint: disable=redefined-builtin


# Algorithm borrowed from Python 3 functools
# + Add support for "list" args
# pylint: disable=dangerous-default-value
def _make_key(
    args: Tuple,
    kwds: Dict,
    kwd_mark: Tuple = (object(),),
    fasttypes: Set[Type] = {int, str},
    type: Callable = type,
    len: Callable = len,
) -> "Union[int, str, _HashedSeq]":
    """Make a cache key from optionally typed positional and keyword arguments
    The key is constructed in a way that is flat as possible rather than
    as a nested structure that would take more memory.
    If there is only a single argument and its data type is known to cache
    its hash value, then that argument is returned without a wrapper.  This
    saves space and improves lookup speed.
    """
    # All of code below relies on kwds preserving the order input by the user.
    # Formerly, we sorted() the kwds before looping.  The new way is *much*
    # faster; however, it means that f(x=1, y=2) will now be treated as a
    # distinct call from f(y=2, x=1) which will be cached separately.
    key = args
    if kwds:
        key += kwd_mark
        for item in kwds.items():
            key += item

    if len(key) == 1 and type(key[0]) in fasttypes:
        return key[0]
    return _HashedSeq(key)


class _HashedSeq(list):
    """This class guarantees that hash() will be called no more than once
    per element.  This is important because the lru_cache() will hash
    the key multiple times on a cache miss.
    """

    __slots__ = ["hashvalue"]

    def __init__(self, tup, hash=hash):
        super().__init__()
        self[:] = tup
        self.hashvalue = hash(tup)

    # FIXME: This is severely broken: list.__hash__ returns None, i.e. lists are *not* hashable!
    # Perhaps we should derive from tuple instead?
    def __hash__(self):
        return self.hashvalue


# TODO: This may be replaced by @functools.lru_cache() in Python 3
class MemoizeCache:
    """Simple unbound in memory cache

    This decorator can be used to remember the results of single functions. These
    are cached in the function context and referenced using the function arguments.
    Examples:
      @cmk.utils.memoize.MemoizeCache
    """

    __slots__ = ["_cache", "mem_func"]

    def __init__(self, function: Callable) -> None:
        self.mem_func = function
        self._cache: Dict[Union[int, str, _HashedSeq], Any] = {}

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        cache_id = _make_key(args, kwargs)

        if cache_id in self._cache:
            return self._cache[cache_id]

        result = self.mem_func(*args, **kwargs)
        self._cache[cache_id] = result
        return result

    def clear(self):
        self._cache.clear()

    def clear_cache(self):
        # naming compatible with lru_cache
        return self.clear()
