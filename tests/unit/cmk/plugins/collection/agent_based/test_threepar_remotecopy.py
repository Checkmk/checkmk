#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.collection.agent_based.threepar_remotecopy import (
    check_threepar_remotecopy,
    discover_threepar_remotecopy,
    parse_threepar_remotecopy,
    THREEPAR_REMOTECOPY_DEFAULT_LEVELS,
)

STRING_TABLE = [['{"mode":2,"status":1,"asyncEnabled":false}']]


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
    section: StringTable,
    expected_discovery_result: Sequence[Service],
) -> None:
    assert (
        list(discover_threepar_remotecopy(parse_threepar_remotecopy(section)))
        == expected_discovery_result
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
    section: StringTable,
    expected_check_result: Sequence[Result],
) -> None:
    assert (
        list(
            check_threepar_remotecopy(
                params=THREEPAR_REMOTECOPY_DEFAULT_LEVELS,
                section=parse_threepar_remotecopy(section),
            )
        )
        == expected_check_result
    )
