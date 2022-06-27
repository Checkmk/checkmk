#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Managing in-memory caches through the execution time of cmk"""

import collections
from functools import lru_cache, wraps
from typing import Dict

import cmk.utils.misc


# Used as decorator wrapper for functools.lru_cache in order to bind the cache to an instance method
# rather than the class method.
def instance_method_lru_cache(*cache_args, **cache_kwargs):
    def cache_decorator(func):
        @wraps(func)
        def cache_factory(self, *args, **kwargs):
            instance_cache = lru_cache(*cache_args, **cache_kwargs)(func)
            instance_cache = instance_cache.__get__(  # pylint: disable=unnecessary-dunder-call
                self, self.__class__
            )
            setattr(self, func.__name__, instance_cache)
            return instance_cache(*args, **kwargs)

        return cache_factory

    return cache_decorator


class CacheManager:
    def __init__(self) -> None:
        self._caches: Dict[str, DictCache] = collections.defaultdict(DictCache)

    def __contains__(self, name: str) -> bool:
        return name in self._caches

    def get(self, name: str) -> "DictCache":
        return self._caches[name]

    def clear(self) -> None:
        self._caches.clear()

    def clear_all(self) -> None:
        for cache in self._caches.values():
            cache.clear()

    def dump_sizes(self) -> Dict[str, int]:
        sizes = {}
        for name, cache in self._caches.items():
            sizes[name] = cmk.utils.misc.total_size(cache)
        return sizes


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
config_cache = CacheManager()

# These caches are not automatically cleared during the whole execution
# time of the current Checkmk process. Single cached may be cleaned
# manually during execution.
runtime_cache = CacheManager()
