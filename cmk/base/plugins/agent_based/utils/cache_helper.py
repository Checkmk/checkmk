#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import NamedTuple
from ..agent_based_api.v1.render import timespan, percent


class CacheInfo(
        NamedTuple("_CacheInfo", [
            ("age", float),
            ("cache_interval", float),
            ("elapsed_lifetime_percent", float),
        ])):
    """
    >>> CacheInfo(age=300,cache_interval=600)
    CacheInfo(age=300, cache_interval=600, elapsed_lifetime_percent=50.0)
    """
    def __new__(
        cls,
        *,
        age: float,
        cache_interval: float,
    ) -> 'CacheInfo':
        return super().__new__(
            cls,
            age=age,
            cache_interval=cache_interval,
            elapsed_lifetime_percent=cls._calculate_elapsed_percent(
                age=age,
                cache_interval=cache_interval,
            ),
        )

    @staticmethod
    def _calculate_elapsed_percent(
        *,
        age: float,
        cache_interval: float,
    ) -> float:
        return 100.0 * age / cache_interval


def render_cache_info(cacheinfo: CacheInfo) -> str:
    """ Renders cache information of local and mrpe services

    We try to mimic the behaviour of cached agent sections.
    Problem here: We need this info on a per-service basis, so we cannot use the section header.
    Solution: Just add an informative message with the same wording as in cmk/gui/plugins/views/utils.py

    >>> render_cache_info(CacheInfo(age=20, cache_interval=40))
    'Cache generated 20 seconds ago, cache interval: 40 seconds, elapsed cache lifespan: 50.00%'
    >>> render_cache_info(CacheInfo(age=-20, cache_interval=40))
    'Cannot reasonably calculate cache metrics (hosts time is running ahead), cache interval: 40 seconds'
    """
    if cacheinfo.age >= 0:
        return (f"Cache generated {timespan(cacheinfo.age)} ago, "
                f"cache interval: {timespan(cacheinfo.cache_interval)}, "
                f"elapsed cache lifespan: {percent(cacheinfo.elapsed_lifetime_percent)}")
    return (f"Cannot reasonably calculate cache metrics (hosts time is running ahead), "
            f"cache interval: {timespan(cacheinfo.cache_interval)}")
