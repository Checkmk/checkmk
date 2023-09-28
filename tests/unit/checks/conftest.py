#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import typing
from collections import abc
from unittest import mock

import pytest

from cmk.utils.caching import cache_manager


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
def clear_config_caches():
    yield
    cache_manager.clear()


class _MockVSManager(typing.NamedTuple):
    active_service_interface: abc.Mapping[str, object]


@pytest.fixture()
def initialised_item_state():
    mock_vs = _MockVSManager({})
    with mock.patch(
        "cmk.base.api.agent_based.value_store._global_state._active_host_value_store",
        mock_vs,
    ):
        yield
