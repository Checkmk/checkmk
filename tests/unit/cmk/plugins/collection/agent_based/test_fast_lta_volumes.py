#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.sectionname import SectionName

from cmk.checkengine.checking import CheckPluginName

from cmk.base.api.agent_based.plugin_classes import (
    CheckFunction,
    DiscoveryFunction,
    SNMPParseFunction,
)

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.lib.df import FILESYSTEM_DEFAULT_PARAMS

parsed = {"Archiv_Test": [("Archiv_Test", 953674.31640625, 944137.5732421875, 0)]}
check_name = "fast_lta_volumes"


# TODO: drop this after migration
@pytest.fixture(scope="module", name="plugin")
def _get_plugin(agent_based_plugins):
    return agent_based_plugins.check_plugins[CheckPluginName(check_name)]


# TODO: drop this after migration
@pytest.fixture(scope="module", name=f"parse_{check_name}")
def _get_parse(agent_based_plugins):
    return agent_based_plugins.snmp_sections[SectionName(check_name)].parse_function


# TODO: drop this after migration
@pytest.fixture(scope="module", name=f"discover_{check_name}")
def _get_discovery_function(plugin):
    return lambda s: plugin.discovery_function(section=s)


# TODO: drop this after migration
@pytest.fixture(scope="module", name=f"check_{check_name}")
def _get_check_function(plugin):
    return lambda i, p, s: plugin.check_function(item=i, params=p, section=s)


def test_parse_fast_lta_volumes(parse_fast_lta_volumes: SNMPParseFunction) -> None:
    assert (
        parse_fast_lta_volumes(
            [[["Archiv_Test", "1000000000000", "10000000000"], ["Archiv_Test_1", "", ""]]]
        )
        == parsed
    )


def test_discovery_fast_lta_volumes(
    discover_fast_lta_volumes: DiscoveryFunction,
) -> None:
    assert list(discover_fast_lta_volumes(parsed)) == [Service(item="Archiv_Test")]


@pytest.mark.usefixtures("initialised_item_state")
def test_check_fast_lta_volumes(check_fast_lta_volumes: CheckFunction) -> None:
    assert list(check_fast_lta_volumes("Archiv_Test", FILESYSTEM_DEFAULT_PARAMS, parsed)) == [
        Result(state=State.OK, summary="Used: 1.00% - 9.31 GiB of 931 GiB"),
        Metric(
            "fs_used",
            9536.7431640625,
            levels=(762939.453125, 858306.884765625),
            boundaries=(0.0, 953674.31640625),
        ),
        Metric("fs_free", 944137.5732421875, boundaries=(0, None)),
        Metric("fs_used_percent", 1.0, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
        Metric("fs_size", 953674.31640625, boundaries=(0.0, None)),
    ]
