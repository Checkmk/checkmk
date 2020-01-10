#!/usr/bin/env python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
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
"""Managing in-memory caches through the execution time of cmk"""

import abc
from typing import cast, Type, Dict  # pylint: disable=unused-import
import six

from cmk.utils.exceptions import MKGeneralException
import cmk.utils.misc


class CacheManager(object):
    def __init__(self):
        # type: () -> None
        self._caches = {}  # type: Dict[str, Cache]

    def exists(self, name):
        # type: (str) -> bool
        return name in self._caches

    def get(self, name, cache_class):
        # type: (str, Type[Cache]) -> Cache
        try:
            return self._caches[name]
        except KeyError:
            if not issubclass(cache_class, Cache):
                raise MKGeneralException("The cache object must be a instance of Cache()")

            self._caches[name] = cache_class()
            return self._caches[name]

    def get_dict(self, name):
        # type: (str) -> DictCache
        return cast(DictCache, self.get(name, DictCache))

    def get_set(self, name):
        # type: (str) -> SetCache
        return cast(SetCache, self.get(name, SetCache))

    def get_list(self, name):
        # type: (str) -> ListCache
        return cast(ListCache, self.get(name, ListCache))

    def clear_all(self):
        # type: () -> None
        for cache in self._caches.values():
            cache.clear()

    def dump_sizes(self):
        # type: () -> Dict[str, int]
        sizes = {}
        for name, cache in self._caches.items():
            sizes[name] = cmk.utils.misc.total_size(cache)
        return sizes


class Cache(six.with_metaclass(abc.ABCMeta, object)):
    _populated = False

    def is_empty(self):
        # type: () -> bool
        """Whether or not there is something in the collection at the moment"""
        return not self

    def is_populated(self):
        # type: () -> bool
        """Whether or not the cache has been marked as populated. This is just a flag
        to tell the caller the initialization state of the cache. It has to be set
        to True manually by using self.set_populated()"""
        return self._populated

    def set_populated(self):
        # type: () -> None
        self._populated = True

    def set_not_populated(self):
        # type: () -> None
        self._populated = False

    @abc.abstractmethod
    def clear(self):
        # type: () -> None
        raise NotImplementedError()


class DictCache(dict, Cache):
    def clear(self):
        # type: () -> None
        super(DictCache, self).clear()
        self.set_not_populated()


## Just a small wrapper round a dict to get some caching specific functionality
## for analysis etc.
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
    def clear(self):
        # type: () -> None
        super(SetCache, self).clear()
        self.set_not_populated()


class ListCache(list, Cache):
    def clear(self):
        # type: () -> None
        del self[:]  # Clear the list in place
        self.set_not_populated()
