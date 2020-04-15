#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access
import pytest
from pathlib2 import Path

from cmk.special_agents.utils import DataCache


class KeksDose(DataCache):
    @property
    def cache_interval(self):
        return 5

    def get_validity_from_args(self, arg):
        return bool(arg)

    def get_live_data(self, arg):
        return "live data"


def test_datacache_init(tmp_path):
    tcache = KeksDose(tmp_path, 'test')
    assert isinstance(tcache._cache_file_dir, Path)
    assert isinstance(tcache._cache_file, Path)
    assert not tcache.debug

    tc_debug = KeksDose(tmp_path, 'test', debug=True)
    assert tc_debug.debug

    with pytest.raises(TypeError):
        DataCache('foo', 'bar')  # pylint: disable=abstract-class-instantiated


def test_datacache_timestamp(tmp_path):
    tcache = KeksDose(tmp_path, 'test')

    assert tcache.cache_timestamp is None  # file doesn't exist yet

    tcache._write_to_cache('')
    assert tcache.cache_timestamp == tcache._cache_file.stat().st_mtime


def test_datacache_valid(monkeypatch, tmp_path):
    tcache = KeksDose(tmp_path, 'test')
    tcache._write_to_cache('cached data')

    valid_time = tcache.cache_timestamp + tcache.cache_interval - 1
    monkeypatch.setattr("time.time", lambda: valid_time)

    assert tcache._cache_is_valid()
    # regular case
    assert tcache.get_data(True) == 'cached data'
    # force live data
    assert tcache.get_data(True, use_cache=False) == 'live data'
    # cache is valid, but get_validity_from_args wants live data
    assert tcache.get_data(False) == 'live data'
    # now live data should be in the cache file
    assert tcache.get_data(True) == 'live data'


def test_datacache_validity(monkeypatch, tmp_path):
    tcache = KeksDose(tmp_path, 'test')
    tcache._write_to_cache('cached data')

    invalid_time = tcache.cache_timestamp + tcache.cache_interval + 1
    monkeypatch.setattr("time.time", lambda: invalid_time)

    assert not tcache._cache_is_valid()
    assert tcache.get_data(True) == 'live data'
