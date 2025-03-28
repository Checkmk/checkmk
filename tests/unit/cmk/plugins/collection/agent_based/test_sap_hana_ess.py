#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.utils.sectionname import SectionName

from cmk.checkengine.plugins import AgentBasedPlugins, CheckPluginName

from cmk.agent_based.v2 import (
    CheckResult,
    DiscoveryResult,
    IgnoreResultsError,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)


@pytest.mark.parametrize(
    "info, expected_result",
    [
        (
            [
                ["[[HXE 90 HXE]]"],
                ["started", "0"],
                ["active", "no"],
            ],
            {"HXE 90 HXE": {"active": "no", "started": 0}},
        ),
        (
            [
                ["[[HXE 90 HXE]]"],
                ["started"],
                ["active", "no"],
            ],
            {"HXE 90 HXE": {"active": "no"}},
        ),
        (
            [
                ["[[HXE 90 HXE]]"],
                ["started", "a"],
                ["active", "no"],
            ],
            {"HXE 90 HXE": {"active": "no"}},
        ),
    ],
)
def test_parse_sap_hana_ess(
    agent_based_plugins: AgentBasedPlugins, info: StringTable, expected_result: Mapping[str, object]
) -> None:
    section_plugin = agent_based_plugins.agent_sections[SectionName("sap_hana_ess")]
    result = section_plugin.parse_function(info)
    assert result == expected_result


@pytest.mark.parametrize(
    "info, expected_result",
    [
        (
            [
                ["[[HXE 90 HXE]]"],
                ["started", "0"],
                ["active", "no"],
            ],
            [Service(item="HXE 90 HXE")],
        ),
    ],
)
def test_inventory_sap_hana_ess(
    agent_based_plugins: AgentBasedPlugins, info: StringTable, expected_result: DiscoveryResult
) -> None:
    section = agent_based_plugins.agent_sections[SectionName("sap_hana_ess")].parse_function(info)
    plugin = agent_based_plugins.check_plugins[CheckPluginName("sap_hana_ess")]
    assert list(plugin.discovery_function(section)) == expected_result


@pytest.mark.parametrize(
    "item, info, expected_result",
    [
        (
            "HXE 90 HXE",
            [
                ["[[HXE 90 HXE]]"],
                ["started", "0"],
                ["active", "no"],
            ],
            [
                Result(state=State.CRIT, summary="Active status: no"),
                Result(state=State.CRIT, summary="Started threads: 0"),
                Metric("threads", 0),
            ],
        ),
        (
            "HXE 90 HXE",
            [
                ["[[HXE 90 HXE]]"],
                ["started", "1"],
                ["active", "yes"],
            ],
            [
                Result(state=State.OK, summary="Active status: yes"),
                Result(state=State.OK, summary="Started threads: 1"),
                Metric("threads", 1),
            ],
        ),
        (
            "HXE 90 HXE",
            [
                ["[[HXE 90 HXE]]"],
                ["started", "1"],
                ["active", "unknown"],
            ],
            [
                Result(state=State.UNKNOWN, summary="Active status: unknown"),
                Result(state=State.OK, summary="Started threads: 1"),
                Metric("threads", 1),
            ],
        ),
    ],
)
def test_check_sap_hana_ess(
    agent_based_plugins: AgentBasedPlugins,
    item: str,
    info: StringTable,
    expected_result: CheckResult,
) -> None:
    section = agent_based_plugins.agent_sections[SectionName("sap_hana_ess")].parse_function(info)
    plugin = agent_based_plugins.check_plugins[CheckPluginName("sap_hana_ess")]
    assert list(plugin.check_function(item, section)) == expected_result


@pytest.mark.parametrize(
    "item, info",
    [
        (
            "HXE 90 HXE",
            [
                ["[[HXE 90 HXE]]"],
            ],
        ),
    ],
)
def test_check_sap_hana_ess_stale(
    agent_based_plugins: AgentBasedPlugins, item: str, info: StringTable
) -> None:
    section = agent_based_plugins.agent_sections[SectionName("sap_hana_ess")].parse_function(info)
    plugin = agent_based_plugins.check_plugins[CheckPluginName("sap_hana_ess")]
    with pytest.raises(IgnoreResultsError):
        list(plugin.check_function(item, section))
