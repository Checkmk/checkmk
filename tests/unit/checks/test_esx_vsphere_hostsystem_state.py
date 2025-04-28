#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.checkengine.plugins import AgentBasedPlugins, CheckPluginName

from cmk.agent_based.v1 import Result, State
from cmk.agent_based.v1.type_defs import CheckResult
from cmk.plugins.vsphere.lib.esx_vsphere import Section


@pytest.mark.parametrize(
    "state, expected_check_result",
    [
        pytest.param(
            "green",
            Result(state=State.OK, summary="Entity state: green"),
            id=("Green is OK"),
        ),
        pytest.param(
            "yellow",
            Result(state=State.WARN, summary="Entity state: yellow"),
            id=("Yellow is WARN"),
        ),
        pytest.param(
            "red",
            Result(state=State.CRIT, summary="Entity state: red"),
            id=("Red is CRIT"),
        ),
        pytest.param(
            "gray",
            Result(state=State.CRIT, summary="Entity state: gray"),
            id=("Gray is CRIT"),
        ),
    ],
)
def test_check_esx_vsphere_hostsystem_cpu_entity_state(
    agent_based_plugins: AgentBasedPlugins, state: str, expected_check_result: CheckResult
) -> None:
    check = agent_based_plugins.check_plugins[CheckPluginName("esx_vsphere_hostsystem_state")]
    assert (
        list(
            check.check_function(
                params={},
                section=Section(
                    [
                        ("overallStatus", [state]),
                        ("runtime.powerState", ["poweredOn"]),
                    ]
                ),
            )
        )[0]
        == expected_check_result
    )


@pytest.mark.parametrize(
    "state, expected_check_result",
    [
        pytest.param(
            "poweredOn",
            Result(state=State.OK, summary="Power state: poweredOn"),
            id=("Powered on is OK"),
        ),
        pytest.param(
            "poweredOff",
            Result(state=State.CRIT, summary="Power state: poweredOff"),
            id=("Powered off is CRIT"),
        ),
        pytest.param(
            "standBy",
            Result(state=State.WARN, summary="Power state: standBy"),
            id=("Stand by is WARN"),
        ),
        pytest.param(
            "unknown",
            Result(state=State.CRIT, summary="Power state: unknown"),
            id=("Unknown is CRIT"),
        ),
    ],
)
def test_check_esx_vsphere_hostsystem_cpu_power_state(
    agent_based_plugins: AgentBasedPlugins, state: str, expected_check_result: CheckResult
) -> None:
    check = agent_based_plugins.check_plugins[CheckPluginName("esx_vsphere_hostsystem_state")]
    assert (
        list(
            check.check_function(
                params={},
                section=Section(
                    [
                        ("overallStatus", ["green"]),
                        ("runtime.powerState", [state]),
                    ]
                ),
            )
        )[1]
        == expected_check_result
    )
