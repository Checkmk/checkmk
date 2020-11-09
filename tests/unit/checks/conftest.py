#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]
from testlib.base import Scenario  # type: ignore[import]


# patch cmk.utils.paths
@pytest.fixture(autouse=True, scope="function")
def patch_cmk_utils_paths(monkeypatch, tmp_path):
    import cmk.utils.paths
    var_dir_path = tmp_path / 'var' / 'check_mk'
    # don't mkdir, check should be able to handle that.
    monkeypatch.setattr(cmk.utils.paths, "var_dir", str(var_dir_path))


# Automatically refresh caches for each test
@pytest.fixture(autouse=True, scope="function")
def clear_config_caches(monkeypatch):
    from cmk.base.caching import config_cache as _config_cache, runtime_cache as _runtime_cache
    _config_cache.reset()
    _runtime_cache.reset()

    ts = Scenario()
    ts.add_host("non-existent-testhost")
    ts.apply(monkeypatch)
