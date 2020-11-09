#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

from testlib.base import Scenario


@pytest.fixture(name="core_scenario")
def fixture_core_scenario(monkeypatch):
    ts = Scenario().add_host("test-host")
    ts.set_option("ipaddresses", {"test-host": "127.0.0.1"})
    return ts.apply(monkeypatch)


# Automatically refresh caches for each test
@pytest.fixture(autouse=True, scope="function")
def clear_config_caches(monkeypatch):
    from cmk.base.caching import config_cache as _config_cache, runtime_cache as _runtime_cache
    _config_cache.reset()
    _runtime_cache.reset()
