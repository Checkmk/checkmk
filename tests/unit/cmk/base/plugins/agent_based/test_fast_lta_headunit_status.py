#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.utils.type_defs import CheckPluginName

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State

check_name = "fast_lta_headunit_status"

# TODO: drop this after migration
@pytest.fixture(scope="module", name="plugin")
def _get_plugin(fix_register):
    return fix_register.check_plugins[CheckPluginName(check_name)]


# TODO: drop this after migration
@pytest.fixture(scope="module", name=f"discover_{check_name}")
def _get_discovery_function(plugin):
    return lambda s: plugin.discovery_function(section=s)


# TODO: drop this after migration
@pytest.fixture(scope="module", name=f"check_{check_name}")
def _get_check_function(plugin):
    return lambda i, p, s: plugin.check_function(item=i, params=p, section=s)


@pytest.mark.parametrize("info, expected", [([[["60", "1", "1"]]], [Service()])])
def test_discovery_fast_lta_headunit_status(
    discover_fast_lta_headunit_status, info, expected
) -> None:
    assert list(discover_fast_lta_headunit_status(info)) == expected


@pytest.mark.parametrize(
    "info, expected",
    [
        (
            [[["60", "1", "1"]]],
            [Result(state=State.OK, summary="Head Unit status is appReady.")],
        ),
        (
            [[["75", "1", "1"]]],
            [Result(state=State.CRIT, summary="Head Unit status is appEnterpriseCubes.")],
        ),
        (
            [[["70", "0", "1"]]],
            [Result(state=State.OK, summary="Head Unit status is appReadOnly.")],
        ),
        (
            [[["99", "0", "1"]]],
            [Result(state=State.CRIT, summary="Head Unit status is 99.")],
        ),
    ],
)
def test_check_fast_lta_headunit_status(check_fast_lta_headunit_status, info, expected) -> None:
    assert list(check_fast_lta_headunit_status(None, {}, info)) == expected
