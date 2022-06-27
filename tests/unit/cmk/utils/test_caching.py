#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.utils.caching


def test_cache_manager() -> None:
    cmk.utils.caching.CacheManager()


def test_create_dict_cache() -> None:
    mgr = cmk.utils.caching.CacheManager()
    key = "test"

    assert key not in mgr
    cache = mgr.get(key)
    assert key in mgr

    assert isinstance(cache, dict)
    assert isinstance(cache, cmk.utils.caching.DictCache)


def test_clear_all() -> None:
    mgr = cmk.utils.caching.CacheManager()

    cache = mgr.get("test_dict")
    assert cache.is_empty()

    cache["asd"] = 1
    cache.update({"a": 1, "b": 3})
    assert not cache.is_empty()

    mgr.clear_all()
    assert cache.is_empty()


def test_populated() -> None:
    mgr = cmk.utils.caching.CacheManager()

    cache = mgr.get("test1")
    assert not cache.is_populated()
    cache.set_populated()
    assert cache.is_populated()
    cache.clear()
    assert not cache.is_populated()
