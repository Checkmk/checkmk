#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.utils.type_defs import CheckPluginName, SectionName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State

parsed = {"Archiv_Test": [("Archiv_Test", 953674.31640625, 944137.5732421875, 0)]}
info = [[["Archiv_Test", "1000000000000", "10000000000"], ["Archiv_Test_1", "", ""]]]
check_name = "fast_lta_volumes"


# TODO: drop this after migration
@pytest.fixture(scope="module", name="plugin")
def _get_plugin(fix_register):
    return fix_register.check_plugins[CheckPluginName(check_name)]


# TODO: drop this after migration
@pytest.fixture(scope="module", name=f"parse_{check_name}")
def _get_parse(fix_register):
    return fix_register.snmp_sections[SectionName(check_name)].parse_function


# TODO: drop this after migration
@pytest.fixture(scope="module", name=f"discover_{check_name}")
def _get_discovery_function(plugin):
    return lambda s: plugin.discovery_function(section=s)


# TODO: drop this after migration
@pytest.fixture(scope="module", name=f"check_{check_name}")
def _get_check_function(plugin):
    return lambda i, p, s: plugin.check_function(item=i, params=p, section=s)


def test_parse_fast_lta_volumes(parse_fast_lta_volumes) -> None:
    assert parse_fast_lta_volumes(info) == parsed


def test_discovery_fast_lta_volumes(discover_fast_lta_volumes) -> None:
    assert list(discover_fast_lta_volumes(parsed)) == [Service(item="Archiv_Test")]


def test_check_fast_lta_volumes(check_fast_lta_volumes) -> None:
    assert list(check_fast_lta_volumes("Archiv_Test", {}, parsed)) == [
        Result(state=State.OK, summary="1.0% used (9.31 of 931 GiB)"),
        Metric(
            "fs_used",
            9536.7431640625,
            levels=(762939.453125, 858306.884765625),
            boundaries=(0.0, 953674.31640625),
        ),
        Metric("fs_size", 953674.31640625),
        Metric("fs_used_percent", 1.0),
    ]
