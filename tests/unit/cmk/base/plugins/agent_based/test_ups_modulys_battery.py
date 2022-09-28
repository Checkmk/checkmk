#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Result, Service, State
from cmk.base.plugins.agent_based.ups_modulys_battery import (
    check_ups_modulys_battery,
    discover_ups_modulys_battery,
    UPSBattery,
    UPSBatterySection,
)


def test_discover_ups_modulys_battery() -> None:
    assert list(
        discover_ups_modulys_battery(
            UPSBattery(
                health=0,
                uptime=0,
                remaining_time_in_min=10,
                capacity=100,
                temperature=45,
            )
        )
    ) == [Service()]


@pytest.mark.parametrize(
    "section, expected_result",
    [
        pytest.param(
            UPSBattery(
                health=0,
                uptime=0,
                remaining_time_in_min=10,
                capacity=100,
                temperature=45,
            ),
            [
                Result(state=State.OK, summary="on mains"),
                Result(state=State.OK, summary="OK"),
            ],
            id="Everything is OK",
        ),
        pytest.param(
            UPSBattery(
                health=0,
                uptime=60,
                remaining_time_in_min=10,
                capacity=100,
                temperature=45,
            ),
            [
                Result(state=State.OK, summary="discharging for 1 minutes"),
                Result(state=State.OK, summary="OK"),
            ],
            id="If the elapsed time is not 0, the desciption gives information in how many minutes the battery will discharge.",
        ),
        pytest.param(
            UPSBattery(
                health=1,
                uptime=0,
                remaining_time_in_min=10,
                capacity=100,
                temperature=45,
            ),
            [
                Result(state=State.OK, summary="on mains"),
                Result(state=State.WARN, summary="battery health weak"),
                Result(state=State.OK, summary="OK"),
            ],
            id="If the battery health is 1, the check result is a WARN state and description that tells that the battery is weak.",
        ),
        pytest.param(
            UPSBattery(
                health=2,
                uptime=0,
                remaining_time_in_min=10,
                capacity=100,
                temperature=45,
            ),
            [
                Result(state=State.OK, summary="on mains"),
                Result(state=State.CRIT, summary="battery needs to be replaced"),
                Result(state=State.OK, summary="OK"),
            ],
            id="If the battery health is 2, the check result is a CRIT state and description that tells that the battery needs to be replaced.",
        ),
        pytest.param(
            UPSBattery(
                health=0,
                uptime=0,
                remaining_time_in_min=10,
                capacity=80,
                temperature=45,
            ),
            [
                Result(state=State.OK, summary="on mains"),
                Result(state=State.CRIT, summary="80 percent charged (warn/crit at 95/90 perc)"),
            ],
            id="If the remaining capacity is less than the crit level, the check result state is CRIT with the appropriate description.",
        ),
        pytest.param(
            UPSBattery(
                health=0,
                uptime=0,
                remaining_time_in_min=10,
                capacity=92,
                temperature=45,
            ),
            [
                Result(state=State.OK, summary="on mains"),
                Result(state=State.WARN, summary="92 percent charged (warn/crit at 95/90 perc)"),
            ],
            id="If the remaining capacity is less than the warn level, the check result state is WARN with the appropriate description.",
        ),
        pytest.param(
            UPSBattery(
                health=0,
                uptime=2,
                remaining_time_in_min=8,
                capacity=100,
                temperature=45,
            ),
            [
                Result(state=State.OK, summary="discharging for 0 minutes"),
                Result(state=State.WARN, summary="8 minutes remaining (warn/crit at 9/7 min)"),
            ],
            id="If the remaining time is less than the warn level, the check result state is WARN with the appropriate description. The elapsed time must not be 0.",
        ),
        pytest.param(
            UPSBattery(
                health=0,
                uptime=2,
                remaining_time_in_min=5,
                capacity=100,
                temperature=45,
            ),
            [
                Result(state=State.OK, summary="discharging for 0 minutes"),
                Result(state=State.CRIT, summary="5 minutes remaining (warn/crit at 9/7 min)"),
            ],
            id="If the remaining time is less than the crit level, the check result state is CRIT with the appropriate description. The elapsed time must not be 0.",
        ),
    ],
)
def test_check_ups_modulys_battery(
    section: UPSBatterySection,
    expected_result: Sequence[Result],
) -> None:
    assert (
        list(
            check_ups_modulys_battery(
                params={"capacity": (95, 90), "battime": (9, 7)}, section=section
            )
        )
        == expected_result
    )
