#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.checkengine.plugins import AgentBasedPlugins, CheckPluginName

from cmk.agent_based.v1 import Result, State
from cmk.agent_based.v1.type_defs import CheckResult
from cmk.plugins.vsphere.lib.esx_vsphere import Section


@pytest.mark.parametrize(
    "section, params, expected_check_result",
    [
        pytest.param(
            Section(
                [
                    ("runtime.inMaintenanceMode", ["false"]),
                ]
            ),
            {"target_state": "false"},
            [Result(state=State.OK, summary="System not in Maintenance mode")],
            id=("Maintenance mode off"),
        ),
        pytest.param(
            Section(
                [
                    ("runtime.inMaintenanceMode", ["false"]),
                ]
            ),
            {"target_state": "true"},
            [Result(state=State.CRIT, summary="System not in Maintenance mode")],
            id=("Maintenance mode off but want on"),
        ),
        pytest.param(
            Section(
                [
                    ("runtime.inMaintenanceMode", ["true"]),
                ]
            ),
            {"target_state": "true"},
            [Result(state=State.OK, summary="System running is in Maintenance mode")],
            id=("Maintenance mode on"),
        ),
        pytest.param(
            Section(
                [
                    ("runtime.inMaintenanceMode", ["true"]),
                ]
            ),
            {"target_state": "false"},
            [Result(state=State.CRIT, summary="System running is in Maintenance mode")],
            id=("Maintenance mode on but want off"),
        ),
    ],
)
def test_check_esx_vsphere_hostsystem_maintenance(
    agent_based_plugins: AgentBasedPlugins,
    section: Section,
    params: Mapping[str, str],
    expected_check_result: CheckResult,
) -> None:
    check = agent_based_plugins.check_plugins[CheckPluginName("esx_vsphere_hostsystem_maintenance")]
    assert list(check.check_function(params=params, section=section)) == expected_check_result
