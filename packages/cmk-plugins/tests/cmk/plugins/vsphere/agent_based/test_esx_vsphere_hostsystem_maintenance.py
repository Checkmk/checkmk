#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping

import pytest

from cmk.agent_based.v2 import CheckResult, Result, State
from cmk.plugins.vsphere.agent_based.esx_vsphere_hostsystem import (
    check_esx_vsphere_hostsystem_maintenance,
)
from cmk.plugins.vsphere.agent_based.esx_vsphere_hostsystem_section import HostSystemSection


@pytest.mark.parametrize(
    "section, params, expected_check_result",
    [
        pytest.param(
            {"runtime.inMaintenanceMode": ["false"]},
            {"target_state": "false"},
            [Result(state=State.OK, summary="System not in Maintenance mode")],
            id=("Maintenance mode off"),
        ),
        pytest.param(
            {"runtime.inMaintenanceMode": ["false"]},
            {"target_state": "true"},
            [Result(state=State.CRIT, summary="System not in Maintenance mode")],
            id=("Maintenance mode off but want on"),
        ),
        pytest.param(
            {"runtime.inMaintenanceMode": ["true"]},
            {"target_state": "true"},
            [Result(state=State.OK, summary="System running is in Maintenance mode")],
            id=("Maintenance mode on"),
        ),
        pytest.param(
            {"runtime.inMaintenanceMode": ["true"]},
            {"target_state": "false"},
            [Result(state=State.CRIT, summary="System running is in Maintenance mode")],
            id=("Maintenance mode on but want off"),
        ),
    ],
)
def test_check_esx_vsphere_hostsystem_maintenance(
    section: HostSystemSection,
    params: Mapping[str, str],
    expected_check_result: CheckResult,
) -> None:
    assert list(check_esx_vsphere_hostsystem_maintenance(params, section)) == expected_check_result
