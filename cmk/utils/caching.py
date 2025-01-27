#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Managing in-memory caches through the execution time of cmk"""

from __future__ import annotations

import collections
from collections.abc import Callable
from functools import lru_cache, wraps
from typing import ParamSpec, TypeVar

import cmk.utils.misc

P = ParamSpec("P")
R = TypeVar("R")


# Used as decorator wrapper for functools.lru_cache in order to bind the cache to an instance method
# rather than the class method.
# FIXME: Nuke this cruel hack below, it is just an ugly workaround for a missing object which should actually hold the cache!
def instance_method_lru_cache(
    maxsize: int | None = 128, typed: bool = False
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    def wrap(f: Callable[P, R]) -> Callable[P, R]:
        @wraps(f)
        def wrapped_f(*args: P.args, **kwargs: P.kwargs) -> R:
            self, *rest = args
            cache_orig = lru_cache(maxsize, typed)(f)
            instance_cache = cache_orig.__get__(self, self.__class__)  # type: ignore[attr-defined]
            setattr(self, f.__name__, instance_cache)
            value: R = instance_cache(*rest, **kwargs)
            return value

        return wrapped_f

    return wrap


class CacheManager:
    def __init__(self) -> None:
        self._caches: dict[str, DictCache] = collections.defaultdict(DictCache)

    def __contains__(self, name: str) -> bool:
        return name in self._caches

    def obtain_cache(self, name: str) -> DictCache:
        """get or create cache with provided name"""
        return self._caches[name]

    def clear(self) -> None:
        self._caches.clear()

    def clear_all(self) -> None:
        for cache in self._caches.values():
            cache.clear()

    def dump_sizes(self) -> dict[str, int]:
        return {name: cmk.utils.misc.total_size(cache) for name, cache in self._caches.items()}


class DictCache(dict):
    _populated = False

    def is_empty(self) -> bool:
        """Whether or not there is something in the collection at the moment"""
        return not self

    def is_populated(self) -> bool:
        """Whether or not the cache has been marked as populated. This is just a flag
        to tell the caller the initialization state of the cache. It has to be set
        to True manually by using self.set_populated()"""
        return self._populated

    def set_populated(self) -> None:
        self._populated = True

    def set_not_populated(self) -> None:
        self._populated = False

    def clear(self) -> None:
        super().clear()
        self.set_not_populated()


# This cache manager holds all caches that rely on the configuration
# and have to be flushed once the configuration is reloaded in the
# keepalive mode
# TODO(sk): Fix it(mutable global implicitly used)
cache_manager = CacheManager()
