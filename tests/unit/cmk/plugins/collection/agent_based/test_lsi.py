#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.checkengine.checking import CheckPluginName

from cmk.base.api.agent_based.plugin_classes import AgentBasedPlugins

from cmk.agent_based.v2 import CheckResult, DiscoveryResult, Result, Service, State
from cmk.plugins.collection.agent_based.lsi import parse_lsi

INFO = [
    ["VolumeID", "286"],
    ["Statusofvolume", "Okay(OKY)"],
    ["TargetID", "15"],
    ["State", "Optimal(OPT)"],
    ["TargetID", "1"],
    ["State", "Optimal(OPT)"],
]


def test_lsi_parsing() -> None:
    result = parse_lsi(INFO)
    assert "disks" in result and "arrays" in result
    assert "286" in result["arrays"]
    assert "1" in result["disks"]
    assert result["disks"]["1"] == "OPT"


@pytest.mark.parametrize(
    "plugin_name,expected",
    [
        (
            "lsi_array",
            [
                Service(item="286"),
            ],
        ),
        (
            "lsi_disk",
            [
                Service(item="15", parameters={"expected_state": "OPT"}),
                Service(item="1", parameters={"expected_state": "OPT"}),
            ],
        ),
    ],
)
def test_lsi_discovery(
    agent_based_plugins: AgentBasedPlugins, plugin_name: str, expected: DiscoveryResult
) -> None:
    plugin = agent_based_plugins.check_plugins[CheckPluginName(plugin_name)]
    section = parse_lsi(INFO)
    assert list(plugin.discovery_function(section=section)) == expected


def test_lsi_array(agent_based_plugins: AgentBasedPlugins) -> None:
    plugin = agent_based_plugins.check_plugins[CheckPluginName("lsi_array")]
    section = parse_lsi(INFO)
    assert list(plugin.check_function(item="286", params={}, section=section)) == [
        Result(state=State.OK, summary="Status is 'Okay(OKY)'")
    ]


@pytest.mark.parametrize(
    "plugin_name,item,params,expected",
    [
        (
            "lsi_disk",
            "1",
            {"expected_state": "OPT"},
            [Result(state=State.OK, summary="Disk has state 'OPT'")],
        ),
        (
            "lsi_disk",
            "15",
            {"expected_state": "OPT"},
            [Result(state=State.OK, summary="Disk has state 'OPT'")],
        ),
    ],
)
def test_lsi(
    agent_based_plugins: AgentBasedPlugins,
    plugin_name: str,
    item: str,
    params: Mapping[str, str],
    expected: CheckResult,
) -> None:
    plugin = agent_based_plugins.check_plugins[CheckPluginName(plugin_name)]
    section = parse_lsi(INFO)
    assert (
        list(
            plugin.check_function(
                item=item,
                params=params,
                section=section,
            )
        )
        == expected
    )
