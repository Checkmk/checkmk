#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import typing
from collections import abc
from unittest import mock

import pytest


@pytest.fixture(autouse=True, scope="session")
def _autouse_fix_register(agent_based_plugins):
    # make agent_based_plugins autouse for this package. "Check(.)" requires it.
    pass


# patch cmk.utils.paths
@pytest.fixture(autouse=True, scope="function")
def patch_cmk_utils_paths(monkeypatch, tmp_path):
    import cmk.utils.paths

    var_dir_path = tmp_path / "var" / "check_mk"
    # don't mkdir, check should be able to handle that.
    monkeypatch.setattr(cmk.utils.paths, "var_dir", var_dir_path)


class _MockVSManager(typing.NamedTuple):
    active_service_interface: abc.Mapping[str, object]


@pytest.fixture()
def initialised_item_state():
    mock_vs = _MockVSManager({})
    with mock.patch(
        "cmk.agent_based.v1.value_store._active_host_value_store",
        mock_vs,
    ):
        yield
