#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib.base import Scenario


@pytest.fixture(autouse=True, scope="session")
def _autouse_fix_register(fix_register):
    # make fix_register autouse for this package. "Check(.)" requires it.
    pass


# patch cmk.utils.paths
@pytest.fixture(autouse=True, scope="function")
def patch_cmk_utils_paths(monkeypatch, tmp_path):
    import cmk.utils.paths

    var_dir_path = tmp_path / "var" / "check_mk"
    # don't mkdir, check should be able to handle that.
    monkeypatch.setattr(cmk.utils.paths, "var_dir", str(var_dir_path))


# Automatically refresh caches for each test
@pytest.fixture(autouse=True, scope="function")
def clear_config_caches(monkeypatch):
    from cmk.utils.caching import config_cache as _config_cache
    from cmk.utils.caching import runtime_cache as _runtime_cache

    _config_cache.clear()
    _runtime_cache.clear()

    ts = Scenario()
    ts.add_host("non-existent-testhost")
    ts.apply(monkeypatch)


@pytest.fixture(autouse=True)
def _autouse_initialised_item_state(initialised_item_state):
    pass
