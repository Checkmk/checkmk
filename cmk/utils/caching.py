#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Managing in-memory caches through the execution time of cmk"""

from typing import cast, Type, Dict

from cmk.utils.exceptions import MKGeneralException
import cmk.utils.misc


class CacheManager:
    def __init__(self) -> None:
        self._caches: Dict[str, DictCache] = {}

    def reset(self) -> None:
        self._caches = {}

    def exists(self, name: str) -> bool:
        return name in self._caches

    def get(self, name: str, cache_class: Type['DictCache']) -> 'DictCache':
        try:
            return self._caches[name]
        except KeyError:
            if not issubclass(cache_class, DictCache):
                raise MKGeneralException("The cache object must be a instance of Cache()")

            self._caches[name] = cache_class()
            return self._caches[name]

    def get_dict(self, name: str) -> 'DictCache':
        return cast(DictCache, self.get(name, DictCache))

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
