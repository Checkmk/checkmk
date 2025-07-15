#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import CheckResult, Result, Service, State, StringTable
from cmk.checkengine.plugins import AgentBasedPlugins, CheckPluginName
from cmk.plugins.collection.agent_based.sap_hana_instance_status import (
    InstanceProcess,
    InstanceStatus,
)
from cmk.utils.sectionname import SectionName


@pytest.mark.parametrize(
    "info, expected_result",
    [
        pytest.param(
            [
                ["[[HXE 98]]"],
                ["instanceStatus: 3"],
                ["OK"],
                [
                    "name",
                    "description",
                    "dispstatus",
                    "textstatus",
                    "starttime",
                    "elapsedtime",
                    "pid",
                ],
                [
                    "hdbdaemon",
                    "HDB Daemon",
                    "GREEN",
                    "Running",
                    "2021 05 19 07:50:33",
                    "0:40:50",
                    "2384",
                ],
                [
                    "hdbcompileserver",
                    "HDB Compileserver",
                    "GREEN",
                    "Running",
                    "2021 05 19 07:50:44",
                    "0:40:39",
                    "3546",
                ],
            ],
            {
                "HXE 98": InstanceStatus(
                    status="3",
                    processes=[
                        InstanceProcess(
                            name="HDB Daemon",
                            state="GREEN",
                            description="Running",
                            elapsed_time=2450.0,
                            pid="2384",
                        ),
                        InstanceProcess(
                            name="HDB Compileserver",
                            state="GREEN",
                            description="Running",
                            elapsed_time=2439.0,
                            pid="3546",
                        ),
                    ],
                )
            },
            id="instance with processes",
        ),
        pytest.param(
            [
                ["[[HXE 98]]"],
                ["instanceStatus: 4"],
            ],
            {"HXE 98": InstanceStatus(status="4")},
            id="instance without processes",
        ),
        pytest.param(
            [
                ["[[HXE 98]]"],
                ["instanceStatus: 3"],
                ["OK"],
                [
                    "name",
                    "description",
                    "dispstatus",
                    "textstatus",
                    "starttime",
                    "elapsedtime",
                    "pid",
                ],
                [
                    "hdbdaemon",
                    "HDB Daemon",
                    "GREEN",
                    "Running",
                    "2021 05 19 07:50:33",
                ],
                [
                    "hdbcompileserver",
                    "HDB Compileserver",
                    "GREEN",
                    "Running",
                    "2021 05 19 07:50:44",
                    "0:40:39",
                    "3546",
                ],
            ],
            {
                "HXE 98": InstanceStatus(
                    status="3",
                    processes=[
                        InstanceProcess(
                            name="HDB Compileserver",
                            state="GREEN",
                            description="Running",
                            elapsed_time=2439.0,
                            pid="3546",
                        ),
                    ],
                )
            },
            id="incomplete process data",
        ),
    ],
)
def test_parse_sap_hana_instance_status(
    agent_based_plugins: AgentBasedPlugins, info: StringTable, expected_result: Mapping[str, object]
) -> None:
    section_plugin = agent_based_plugins.agent_sections[SectionName("sap_hana_instance_status")]
    assert section_plugin.parse_function(info) == expected_result


@pytest.mark.parametrize(
    "info, expected_result",
    [
        (
            [
                ["[[HXE 98]]"],
                ["instanceStatus: 3"],
                ["OK"],
                [
                    "name",
                    "description",
                    "dispstatus",
                    "textstatus",
                    "starttime",
                    "elapsedtime",
                    "pid",
                ],
                [
                    "hdbdaemon",
                    "HDB Daemon",
                    "GREEN",
                    "Running",
                    "2021 05 19 07:50:33",
                    "0:40:50",
                    "2384",
                ],
                [
                    "hdbcompileserver",
                    "HDB Compileserver",
                    "GREEN",
                    "Running",
                    "2021 05 19 07:50:44",
                    "0:40:39",
                    "3546",
                ],
            ],
            [Service(item="HXE 98")],
        ),
    ],
)
def test_inventory_sap_hana_instance_status(
    agent_based_plugins: AgentBasedPlugins, info: StringTable, expected_result: Sequence[Service]
) -> None:
    section = agent_based_plugins.agent_sections[
        SectionName("sap_hana_instance_status")
    ].parse_function(info)
    plugin = agent_based_plugins.check_plugins[CheckPluginName("sap_hana_instance_status")]
    assert list(plugin.discovery_function(section)) == expected_result


@pytest.mark.parametrize(
    "item, info, expected_result",
    [
        (
            "HXE 98",
            [
                ["[[HXE 98]]"],
                ["instanceStatus: 4"],
            ],
            [Result(state=State.CRIT, summary="All processes stopped")],
        ),
        (
            "HXE 99",
            [
                ["[[HXE 98]]"],
                ["instanceStatus: 4"],
            ],
            [],
        ),
        (
            "HXE 98",
            [
                ["[[HXE 98]]"],
                ["instanceStatus: 3"],
                ["OK"],
                [
                    "name",
                    "description",
                    "dispstatus",
                    "textstatus",
                    "starttime",
                    "elapsedtime",
                    "pid",
                ],
                [
                    "hdbdaemon",
                    "HDB Daemon",
                    "GREEN",
                    "Running",
                    "2021 05 19 07:50:33",
                    "0:40:50",
                    "2384",
                ],
                [
                    "hdbcompileserver",
                    "HDB Compileserver",
                    "RED",
                    "Running",
                    "2021 05 19 07:50:44",
                    "0:40:39",
                    "3546",
                ],
            ],
            [
                Result(state=State.OK, summary="OK"),
                Result(
                    state=State.OK,
                    summary="HDB Daemon: Running for 40 minutes 50 seconds, PID: 2384",
                ),
                Result(
                    state=State.WARN,
                    summary="HDB Compileserver: Running for 40 minutes 39 seconds, PID: 3546",
                ),
            ],
        ),
    ],
)
def test_check_sap_hana_instance_status(
    agent_based_plugins: AgentBasedPlugins,
    item: str,
    info: StringTable,
    expected_result: CheckResult,
) -> None:
    section = agent_based_plugins.agent_sections[
        SectionName("sap_hana_instance_status")
    ].parse_function(info)
    plugin = agent_based_plugins.check_plugins[CheckPluginName("sap_hana_instance_status")]
    assert list(plugin.check_function(item, section)) == expected_result
