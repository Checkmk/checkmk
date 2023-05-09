#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from testlib import Check  # type: ignore[import]

from cmk.base.api.agent_based.checking_classes import CheckResult
from cmk.base.plugins.agent_based.utils.esx_vsphere import Section


@pytest.mark.parametrize(
    "state, expected_check_result",
    [
        pytest.param(
            "green",
            (0, "Entity state: green"),
            id=("Green is OK"),
        ),
        pytest.param(
            "yellow",
            (1, "Entity state: yellow"),
            id=("Yellow is WARN"),
        ),
        pytest.param(
            "red",
            (2, "Entity state: red"),
            id=("Red is CRIT"),
        ),
        pytest.param(
            "gray",
            (2, "Entity state: gray"),
            id=("Gray is CRIT"),
        ),
    ],
)
@pytest.mark.usefixtures("config_load_all_checks")
def test_check_esx_vsphere_hostsystem_cpu_entity_state(state: str,
                                                       expected_check_result: CheckResult) -> None:
    check = Check("esx_vsphere_hostsystem.state")
    assert (list(
        check.run_check(
            None,
            {},
            Section([
                ("overallStatus", [state]),
                ("runtime.powerState", ["poweredOn"]),
            ]),
        ))[0] == expected_check_result)


@pytest.mark.parametrize(
    "state, expected_check_result",
    [
        pytest.param(
            "poweredOn",
            (0, "Power state: poweredOn"),
            id=("Powered on is OK"),
        ),
        pytest.param(
            "poweredOff",
            (2, "Power state: poweredOff"),
            id=("Powered off is CRIT"),
        ),
        pytest.param(
            "standBy",
            (1, "Power state: standBy"),
            id=("Stand by is WARN"),
        ),
        pytest.param(
            "unknown",
            (2, "Power state: unknown"),
            id=("Unknown is CRIT"),
        ),
    ],
)
@pytest.mark.usefixtures("config_load_all_checks")
def test_check_esx_vsphere_hostsystem_cpu_power_state(state: str,
                                                      expected_check_result: CheckResult) -> None:
    check = Check("esx_vsphere_hostsystem.state")
    assert (list(
        check.run_check(
            None,
            {},
            Section([
                ("overallStatus", ["green"]),
                ("runtime.powerState", [state]),
            ]),
        ))[1] == expected_check_result)
