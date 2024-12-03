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
    cache.clear()


def test_set_and_get_last_automation_reload(cache: Cache) -> None:
    now = time.time()
    cache.store_last_automation_helper_reload(now)
    assert cache.last_automation_helper_reload == now


def test_last_automation_reload_unset(cache: Cache) -> None:
    assert cache.last_automation_helper_reload == 0.0


def test_set_and_get_last_change_detected(cache: Cache) -> None:
    now = time.time()
    cache.store_last_detected_change(now)
    assert cache.last_detected_change == now


def test_last_change_detected_unset(cache: Cache) -> None:
    assert cache.last_detected_change == 0.0
