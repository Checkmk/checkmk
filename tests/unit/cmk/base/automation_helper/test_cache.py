#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Generator

import pytest
from fakeredis import FakeRedis

from cmk.base.automation_helper._cache import Cache


@pytest.fixture(name="cache")
def get_cache() -> Generator[Cache]:
    cache = Cache.setup(client=FakeRedis())
    yield cache


def test_set_and_get_last_change_detected(cache: Cache) -> None:
    now = time.time()
    cache.store_last_detected_change(now)
    assert cache.get_last_detected_change() == now


def test_get_last_change_detected_unset(cache: Cache) -> None:
    assert cache.get_last_detected_change() == 0.0


def test_reload_required(cache: Cache) -> None:
    cache.store_last_detected_change(1.0)
    assert cache.reload_required(0.0)
