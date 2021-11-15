#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from datetime import datetime
from pathlib import Path
from typing import Any

import pytest

from cmk.special_agents.utils import DataCache, get_seconds_since_midnight


class KeksDose(DataCache):
    @property
    def cache_interval(self) -> int:
        return 5

    def get_validity_from_args(self, *args: Any) -> bool:
        return bool(args[0])

    def get_live_data(self, *args: Any) -> Any:
        return "live data"


def test_datacache_init(tmp_path):
    tcache = KeksDose(tmp_path, "test")
    assert isinstance(tcache._cache_file_dir, Path)
    assert isinstance(tcache._cache_file, Path)
    assert not tcache.debug

    tc_debug = KeksDose(tmp_path, "test", debug=True)
    assert tc_debug.debug


def test_datacache_timestamp(tmp_path):
    tcache = KeksDose(tmp_path, "test")

    assert tcache.cache_timestamp is None  # file doesn't exist yet

    tcache._write_to_cache("")
    assert tcache.cache_timestamp == tcache._cache_file.stat().st_mtime


def test_datacache_valid(monkeypatch, tmp_path):
    tcache = KeksDose(tmp_path, "test")
    tcache._write_to_cache("cached data")

    valid_time = tcache.cache_timestamp + tcache.cache_interval - 1
    monkeypatch.setattr("time.time", lambda: valid_time)

    assert tcache._cache_is_valid()
    # regular case
    assert tcache.get_data(True) == "cached data"
    # force live data
    assert tcache.get_data(True, use_cache=False) == "live data"
    # cache is valid, but get_validity_from_args wants live data
    assert tcache.get_data(False) == "live data"
    # now live data should be in the cache file
    assert tcache.get_data(True) == "live data"


def test_datacache_validity(monkeypatch, tmp_path):
    tcache = KeksDose(tmp_path, "test")
    tcache._write_to_cache("cached data")

    invalid_time = tcache.cache_timestamp + tcache.cache_interval + 1
    monkeypatch.setattr("time.time", lambda: invalid_time)

    assert not tcache._cache_is_valid()
    assert tcache.get_data(True) == "live data"


@pytest.mark.parametrize(
    "now, result",
    [
        ("2020-07-24 00:00:16.0", 16.0),
        ("2020-07-13 00:01:00.194", 60.194),
    ],
)
def test_get_seconds_since_midnight(now, result):
    now = datetime.strptime(now, "%Y-%m-%d %H:%M:%S.%f")
    assert get_seconds_since_midnight(now) == result
