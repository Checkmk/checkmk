#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.checkengine.plugins import CheckPluginName

from cmk.base.api.agent_based.plugin_classes import CheckFunction, DiscoveryFunction

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.lib.df import FILESYSTEM_DEFAULT_PARAMS

info = [["8001591181312", "3875508482048"]]
check_name = "fast_lta_silent_cubes_capacity"


# TODO: drop this after migration
@pytest.fixture(scope="module", name="plugin")
def _get_plugin(agent_based_plugins):
    return agent_based_plugins.check_plugins[CheckPluginName(check_name)]


# TODO: drop this after migration
@pytest.fixture(scope="module", name=f"discover_{check_name}")
def _get_discovery_function(plugin):
    return lambda s: plugin.discovery_function(section=s)


# TODO: drop this after migration
@pytest.fixture(scope="module", name=f"check_{check_name}")
def _get_check_function(plugin):
    return lambda i, p, s: plugin.check_function(item=i, params=p, section=s)


def test_discovery_fast_lta_silent_cube_capacity(
    discover_fast_lta_silent_cubes_capacity: DiscoveryFunction,
) -> None:
    assert list(discover_fast_lta_silent_cubes_capacity(info)) == [Service(item="Total")]


@pytest.mark.usefixtures("initialised_item_state")
def test_check_fast_lta_silent_cube_capacity(
    check_fast_lta_silent_cubes_capacity: CheckFunction,
) -> None:
    actual_check_results = list(
        check_fast_lta_silent_cubes_capacity(None, FILESYSTEM_DEFAULT_PARAMS, info)
    )
    expected_check_results = [
        Result(state=State.OK, summary="Used: 48.43% - 3.52 TiB of 7.28 TiB"),
        Metric("fs_used", 3695972.90234375, levels=(6104729.6, 6867820.8), boundaries=(0.0, None)),
        Metric("fs_free", 3934939.09765625, boundaries=(0.0, None)),
        Metric("fs_used_percent", 48.434222571872795, levels=(80.0, 90.0), boundaries=(0.0, 100.0)),
    ]

    assert [r for r in actual_check_results if isinstance(r, Result)] == [
        r for r in expected_check_results if isinstance(r, Result)
    ]
    for actual_metric, expected_metric in zip(
        [m for m in actual_check_results if isinstance(m, Metric)],
        [m for m in expected_check_results if isinstance(m, Metric)],
    ):
        assert actual_metric.name == expected_metric.name
        assert actual_metric.value == expected_metric.value
        if hasattr(actual_metric, "levels"):
            assert actual_metric.levels[0] == pytest.approx(expected_metric.levels[0])
            assert actual_metric.levels[1] == pytest.approx(expected_metric.levels[1])
