#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2019             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.
"""A helper module providing simple caching mechanism (without invalidation).
It provides a decorator that can be used to cache function results based on the
given function arguments."""

from typing import Type, Union, Callable, Tuple, Dict, Set, Any  # pylint: disable=unused-import

# The functions that violate this checker are borrowed from official python
# code and are done for performance reasons.
# pylint: disable=redefined-builtin


# Algorithm borrowed from Python 3 functools
# + Add support for "list" args
# pylint: disable=dangerous-default-value
def _make_key(args, kwds, kwd_mark=(object(),), fasttypes={int, str}, type=type, len=len):
    # type: (Tuple, Dict, Tuple, Set[Type], Callable, Callable) -> Union[int, str, _HashedSeq]
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
    """ This class guarantees that hash() will be called no more than once
        per element.  This is important because the lru_cache() will hash
        the key multiple times on a cache miss.
    """

    __slots__ = ['hashvalue']

    def __init__(self, tup, hash=hash):
        super(_HashedSeq, self).__init__()
        self[:] = tup
        self.hashvalue = hash(tup)

    def __hash__(self):
        # type: () -> int
        return self.hashvalue


# TODO: This may be replaced by @functools.lru_cache() in Python 3
class MemoizeCache(object):
    """Simple unbound in memory cache

This decorator can be used to remember the results of single functions. These
are cached in the function context and referenced using the function arguments.
Examples:
  @cmk.utils.memoize.MemoizeCache

"""
    __slots__ = ["_logger", "_cache", "mem_func"]

    def __init__(self, function):
        # type: (Callable) -> None
        self.mem_func = function
        self._cache = {}  # type: Dict[Union[int, str, _HashedSeq], Any]

    def __call__(self, *args, **kwargs):
        # type: (Any, Any) -> Any
        cache_id = _make_key(args, kwargs)

        if cache_id in self._cache:
            return self._cache[cache_id]

        result = self.mem_func(*args, **kwargs)
        self._cache[cache_id] = result
        return result

    def clear(self):
        self._cache.clear()
