#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.base.caching


def test_cache_manager():
    cmk.base.caching.CacheManager()


def test_create_dict_cache():
    mgr = cmk.base.caching.CacheManager()

    assert not mgr.exists("test_dict")
    cache = mgr.get_dict("test_dict")
    assert mgr.exists("test_dict")

    assert isinstance(cache, dict)
    assert isinstance(cache, cmk.base.caching.DictCache)
    assert isinstance(cache, cmk.base.caching.Cache)


def test_create_set_cache():
    mgr = cmk.base.caching.CacheManager()

    assert not mgr.exists("test")
    cache = mgr.get_set("test")
    assert mgr.exists("test")

    assert isinstance(cache, set)
    assert isinstance(cache, cmk.base.caching.SetCache)
    assert isinstance(cache, cmk.base.caching.Cache)


def test_create_list_cache():
    mgr = cmk.base.caching.CacheManager()

    assert not mgr.exists("test")
    cache = mgr.get_list("test")
    assert mgr.exists("test")

    assert isinstance(cache, list)
    assert isinstance(cache, cmk.base.caching.ListCache)
    assert isinstance(cache, cmk.base.caching.Cache)


def test_clear_all():
    mgr = cmk.base.caching.CacheManager()

    list_cache = mgr.get_list("test_list")
    assert list_cache.is_empty()

    list_cache.append("123")
    list_cache += ["1", "2"]
    assert not list_cache.is_empty()

    dict_cache = mgr.get_dict("test_dict")
    assert dict_cache.is_empty()

    dict_cache["asd"] = 1
    dict_cache.update({"a": 1, "b": 3})
    assert not dict_cache.is_empty()

    set_cache = mgr.get_set("test_set")
    assert set_cache.is_empty()

    set_cache.add("1")
    set_cache.add("1")
    assert not set_cache.is_empty()

    mgr.clear_all()
    assert list_cache.is_empty()
    assert dict_cache.is_empty()
    assert set_cache.is_empty()


def test_populated():
    mgr = cmk.base.caching.CacheManager()

    cache1 = mgr.get_set("test1")
    assert not cache1.is_populated()
    cache1.set_populated()
    assert cache1.is_populated()
    cache1.clear()
    assert not cache1.is_populated()

    cache2 = mgr.get_dict("test2")
    assert not cache2.is_populated()
    cache2.set_populated()
    assert cache2.is_populated()
    cache2.clear()
    assert not cache2.is_populated()

    cache3 = mgr.get_list("test3")
    assert not cache3.is_populated()
    cache3.set_populated()
    assert cache3.is_populated()
    cache3.clear()
    assert not cache3.is_populated()
