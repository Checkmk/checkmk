#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import typing
from collections import abc
from unittest import mock

import pytest

from tests.testlib.base import Scenario

from cmk.utils.hostaddress import HostName


@pytest.fixture(name="core_scenario")
def fixture_core_scenario(monkeypatch):
    ts = Scenario()
    ts.add_host(HostName("test-host"))
    ts.set_option("ipaddresses", {"test-host": "127.0.0.1"})
    return ts.apply(monkeypatch)


# Automatically refresh caches for each test
@pytest.fixture(autouse=True, scope="function")
def clear_config_caches(monkeypatch):
    from cmk.utils.caching import config_cache as _config_cache
    from cmk.utils.caching import runtime_cache as _runtime_cache

    _config_cache.clear()
    _runtime_cache.clear()


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
