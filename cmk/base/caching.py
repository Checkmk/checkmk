#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Managing in-memory caches through the execution time of cmk"""

import abc
from typing import cast, Type, Dict

from cmk.utils.exceptions import MKGeneralException
import cmk.utils.misc


class CacheManager:
    def __init__(self) -> None:
        self._caches: Dict[str, Cache] = {}

    def reset(self) -> None:
        self._caches = {}

    def exists(self, name: str) -> bool:
        return name in self._caches

    def get(self, name: str, cache_class: Type['Cache']) -> 'Cache':
        try:
            return self._caches[name]
        except KeyError:
            if not issubclass(cache_class, Cache):
                raise MKGeneralException("The cache object must be a instance of Cache()")

            self._caches[name] = cache_class()
            return self._caches[name]

    def get_dict(self, name: str) -> 'DictCache':
        return cast(DictCache, self.get(name, DictCache))

    def get_set(self, name: str) -> 'SetCache':
        return cast(SetCache, self.get(name, SetCache))

    def get_list(self, name: str) -> 'ListCache':
        return cast(ListCache, self.get(name, ListCache))

    def clear_all(self) -> None:
        for cache in self._caches.values():
            cache.clear()

    def dump_sizes(self) -> Dict[str, int]:
        sizes = {}
        for name, cache in self._caches.items():
            sizes[name] = cmk.utils.misc.total_size(cache)
        return sizes


class Cache(metaclass=abc.ABCMeta):
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

    @abc.abstractmethod
    def clear(self) -> None:
        raise NotImplementedError()


class DictCache(dict, Cache):
    def clear(self) -> None:
        super(DictCache, self).clear()
        self.set_not_populated()


# Just a small wrapper round a dict to get some caching specific functionality
# for analysis etc.
#class DictCacheStats(DictCache):
#    def __init__(self, *args, **kwargs):
#        super(DictCacheStats, self).__init__(*args, **kwargs)
#        self._num_hits = 0
#        self._num_misses = 0
#        self._num_sets = 0
#
#    def __getitem__(self, y):
#        try:
#            result = super(DictCacheStats, self).__getitem__(y)
#            self._num_hits += 1
#            return result
#        except KeyError:
#            self._num_misses += 1
#            raise
#
#    def __setitem__(self, i, y):
#        self._num_sets += 1
#        super(DictCacheStats, self).__setitem__(i, y)
#
#    def get_stats(self):
#        return {
#            "sets": self._num_sets,
#            "hits": self._num_hits,
#            "misses": self._num_misses,
#            "items": len(self),
#        }


class SetCache(set, Cache):
    def clear(self) -> None:
        super(SetCache, self).clear()
        self.set_not_populated()


class ListCache(list, Cache):
    def clear(self) -> None:
        del self[:]  # Clear the list in place
        self.set_not_populated()


# This cache manager holds all caches that rely on the configuration
# and have to be flushed once the configuration is reloaded in the
# keepalive mode
config_cache = CacheManager()

# These caches are not automatically cleared during the whole execution
# time of the current Checkmk process. Single cached may be cleaned
# manually during execution.
runtime_cache = CacheManager()
