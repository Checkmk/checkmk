#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping

import pytest

from testlib import Check  # type: ignore[import]

from cmk.base.api.agent_based.checking_classes import CheckResult
from cmk.base.plugins.agent_based.utils.esx_vsphere import Section


@pytest.mark.parametrize(
    "section, params, expected_check_result",
    [
        pytest.param(
            Section([
                ("runtime.inMaintenanceMode", ["false"]),
            ]),
            {"target_state": "false"},
            [0, "System not in Maintenance mode"],
            id=("Maintenance mode off"),
        ),
        pytest.param(
            Section([
                ("runtime.inMaintenanceMode", ["false"]),
            ]),
            {"target_state": "true"},
            [2, "System not in Maintenance mode"],
            id=("Maintenance mode off but want on"),
        ),
        pytest.param(
            Section([
                ("runtime.inMaintenanceMode", ["true"]),
            ]),
            {"target_state": "true"},
            [0, "System running is in Maintenance mode"],
            id=("Maintenance mode on"),
        ),
        pytest.param(
            Section([
                ("runtime.inMaintenanceMode", ["true"]),
            ]),
            {"target_state": "false"},
            [2, "System running is in Maintenance mode"],
            id=("Maintenance mode on but want off"),
        ),
    ],
)
@pytest.mark.usefixtures("config_load_all_checks")
def test_check_esx_vsphere_hostsystem_maintenance(section: Section, params: Mapping[str, str],
                                                  expected_check_result: CheckResult) -> None:
    check = Check("esx_vsphere_hostsystem.maintenance")
    assert list(check.run_check(None, params, section)) == expected_check_result
