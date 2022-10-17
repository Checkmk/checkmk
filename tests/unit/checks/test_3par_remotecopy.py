#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from tests.unit.conftest import FixRegister

from cmk.utils.type_defs import CheckPluginName, SectionName

from cmk.base.api.agent_based.checking_classes import CheckPlugin
from cmk.base.api.agent_based.type_defs import StringTable
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State

STRING_TABLE = [['{"mode":2,"status":1,"asyncEnabled":false}']]

THREEPAR_REMOTECOPY_DEFAULT_LEVELS = {
    1: 0,  # NORMAL
    2: 1,  # STARTUP
    3: 1,  # SHUTDOWN
    4: 0,  # ENABLE
    5: 2,  # DISABLE
    6: 2,  # INVALID
    7: 1,  # NODEDUP
    8: 0,  # UPGRADE
}


@pytest.fixture(name="check")
def _3par_remotecopy_check_plugin(fix_register: FixRegister) -> CheckPlugin:
    return fix_register.check_plugins[CheckPluginName("3par_remotecopy")]


@pytest.mark.parametrize(
    "section, expected_discovery_result",
    [
        pytest.param(
            STRING_TABLE,
            [
                Service(),
            ],
            id="For every item from the section that has a mode of STARTED or STOPPED, a Service is created.",
        ),
        pytest.param(
            [],
            [],
            id="If there are no items in the input, nothing is discovered.",
        ),
        pytest.param(
            [['{"mode":1,"status":1,"asyncEnabled":false}']],
            [],
            id="If the mode is NONE, no Service is discovered.",
        ),
    ],
)
def test_discover_3par_remotecopy(
    check: CheckPlugin,
    fix_register: FixRegister,
    section: StringTable,
    expected_discovery_result: Sequence[Service],
) -> None:
    parse_3par_remotecopy = fix_register.agent_sections[
        SectionName("3par_remotecopy")
    ].parse_function
    assert (
        list(check.discovery_function(parse_3par_remotecopy(section))) == expected_discovery_result
    )


@pytest.mark.parametrize(
    "section, expected_check_result",
    [
        pytest.param(
            [],
            [
                Result(state=State.UNKNOWN, summary="Mode: NONE"),
                Result(state=State.CRIT, summary="Status: INVALID"),
            ],
            id="If the mode is unknown, the first check result is UNKNOWN. If the status is unknown, the second check result is CRIT.",
        ),
        pytest.param(
            STRING_TABLE,
            [
                Result(state=State.OK, summary="Mode: STARTED"),
                Result(state=State.OK, summary="Status: NORMAL"),
            ],
            id="If the mode is STARTED, the first check result is OK. If the status is NORMAL or ENABLE or UPGRADE, the check result is OK.",
        ),
        pytest.param(
            [['{"mode":3,"status":7,"asyncEnabled":false}']],
            [
                Result(state=State.CRIT, summary="Mode: STOPPED"),
                Result(state=State.WARN, summary="Status: NODEDUP"),
            ],
            id="If the mode is STOPPED, the first check result is CRIT. If the status is STARTUP or SHUTDOWN or NODEDUP, the check result is WARN.",
        ),
        pytest.param(
            [['{"mode":2,"status":5,"asyncEnabled":false}']],
            [
                Result(state=State.OK, summary="Mode: STARTED"),
                Result(state=State.CRIT, summary="Status: DISABLE"),
            ],
            id="If the status is DISABLE or INVALID, the check result is CRIT.",
        ),
    ],
)
def test_check_3par_remotecopy(
    check: CheckPlugin,
    fix_register: FixRegister,
    section: StringTable,
    expected_check_result: Sequence[Result],
) -> None:
    parse_3par_remotecopy = fix_register.agent_sections[
        SectionName("3par_remotecopy")
    ].parse_function
    assert (
        list(
            check.check_function(
                item="",
                params=THREEPAR_REMOTECOPY_DEFAULT_LEVELS,
                section=parse_3par_remotecopy(section),
            )
        )
        == expected_check_result
    )
