#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.type_defs import CheckPluginName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable

_PLUGIN = CheckPluginName("fireeye_quarantine")


# TODO: drop this after migration
@pytest.fixture(scope="module", name="plugin")
def _get_plugin(fix_register):
    return fix_register.check_plugins[_PLUGIN]


# TODO: drop this after migration
@pytest.fixture(scope="module", name=f"discover_{_PLUGIN}")
def _get_discovery_function(plugin):
    return lambda s: plugin.discovery_function(section=s)


# TODO: drop this after migration
@pytest.fixture(scope="module", name=f"check_{_PLUGIN}")
def _get_check_function(plugin):
    return lambda p, s: plugin.check_function(params=p, section=s)


@pytest.fixture(scope="module", name="section")
def _get_section() -> StringTable:
    return [["42"]]


def test_discover_nothing(discover_fireeye_quarantine) -> None:
    assert not list(discover_fireeye_quarantine([]))


def test_discover_somehting(discover_fireeye_quarantine, section: StringTable) -> None:
    assert list(discover_fireeye_quarantine(section)) == [Service()]


def test_check_ok(check_fireeye_quarantine, section: StringTable) -> None:
    assert list(check_fireeye_quarantine({"usage": (50, 100)}, section)) == [
        Result(state=State.OK, summary="Usage: 42.00%"),
        Metric("quarantine", 42.0, levels=(50.0, 100.0)),
    ]


def test_check_warn(check_fireeye_quarantine, section: StringTable) -> None:
    assert list(check_fireeye_quarantine({"usage": (23, 50)}, section)) == [
        Result(state=State.WARN, summary="Usage: 42.00% (warn/crit at 23.00%/50.00%)"),
        Metric("quarantine", 42.0, levels=(23.0, 50.0)),
    ]


def test_check_crit(check_fireeye_quarantine, section: StringTable) -> None:
    assert list(check_fireeye_quarantine({"usage": (23, 36)}, section)) == [
        Result(state=State.CRIT, summary="Usage: 42.00% (warn/crit at 23.00%/36.00%)"),
        Metric("quarantine", 42.0, levels=(23.0, 36.0)),
    ]
