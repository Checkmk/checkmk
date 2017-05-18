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

from cmk.exceptions import MKGeneralException

import cmk_base.utils

class CacheManager(object):
    def __init__(self):
        self._caches = {}


    def exists(self, name):
        return name in self._caches


    def _get(self, name, cache_class):
        try:
            return self._caches[name]
        except KeyError:
            if not issubclass(cache_class, Cache):
                raise MKGeneralException("The cache object must be a instance of Cache()")

            self._caches[name] = cache_class()
            return self._caches[name]


    def get_dict(self, name):
        return self._get(name, DictCache)


    def get_set(self, name):
        return self._get(name, SetCache)


    def get_list(self, name):
        return self._get(name, ListCache)


    def clear_all(self):
        for cache in self._caches.values():
            cache.clear()


    def dump_sizes(self):
        sizes = {}
        for name, cache in self._caches.items():
            sizes[name] = cmk_base.utils.total_size(cache)
        return sizes



class Cache(object):
    def is_empty(self):
        return not self


# Just a small wrapper round a dict to get some caching specific functionality
# for analysis etc.
class DictCache(dict, Cache):
    pass


class SetCache(set, Cache):
    pass


class ListCache(list, Cache):
    def clear(self):
        del self[:] # Clear the list in place
