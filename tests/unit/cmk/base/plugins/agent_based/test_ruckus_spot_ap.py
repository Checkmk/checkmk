#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Final

import pytest

from cmk.utils.type_defs import CheckPluginName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State

# reverse engineered section from the plugin. No idea if this is correct.
SECTION: Final = {
    "1": [
        ["Stuart", 2],
        ["Dave", 1],
    ],
    "2": [
        ["Kevin", 0],
        ["Bob", 1],
    ],
}


# TODO: drop this after migration
@pytest.fixture(scope="module", name="plugin")
def _get_plugin(fix_register):
    return fix_register.check_plugins[CheckPluginName("ruckus_spot_ap")]


# TODO: drop this after migration
@pytest.fixture(scope="module", name="discover_ruckus_spot_ap")
def _get_discovery_function(plugin):
    return lambda s: plugin.discovery_function(section=s)


# TODO: drop this after migration
@pytest.fixture(scope="module", name="check_ruckus_spot_ap")
def _get_check_function(plugin):
    return lambda i, p, s: plugin.check_function(item=i, params=p, section=s)


def test_discovery(discover_ruckus_spot_ap) -> None:
    assert [*discover_ruckus_spot_ap(SECTION)] == [
        Service(
            item="2.4 GHz", parameters={"auto-migration-wrapper-key": ((None, None), (None, None))}
        ),
        Service(
            item="5 GHz", parameters={"auto-migration-wrapper-key": ((None, None), (None, None))}
        ),
    ]


def test_check_no_data(check_ruckus_spot_ap) -> None:
    assert not [*check_ruckus_spot_ap("2.4 GHz", {}, {})]


def test_check(check_ruckus_spot_ap) -> None:
    params = {"auto-migration-wrapper-key": ((0, 1), (2, 3))}
    assert [*check_ruckus_spot_ap("5 GHz", params, SECTION)] == [
        Result(state=State.OK, summary="Devices: 2"),
        Metric("ap_devices_total", 2.0),
        Metric("ap_devices_drifted", 0.0, levels=(0.0, 1.0)),
        Result(state=State.WARN, summary="Drifted: 0 (warn/crit at 0/1)"),
        Metric("ap_devices_not_responding", 1.0, levels=(2.0, 3.0)),
        Result(state=State.OK, summary="Not responding: 1"),
    ]
