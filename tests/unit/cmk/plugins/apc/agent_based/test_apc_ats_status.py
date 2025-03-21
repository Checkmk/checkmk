#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping

import pytest

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.apc.agent_based.apc_ats_status import (
    check_apc_ats_status,
    discover_apc_ats_status,
    parse_apc_ats_status,
)
from cmk.plugins.apc.lib.apc_ats import (
    CommunictionStatus,
    OverCurrentStatus,
    PowerSource,
    PowerSupplyStatus,
    RedunandancyStatus,
    Source,
    Status,
)

STRING_TABLE_1 = [["2", "2", "2", "2", "2", "2", "", ""]]
STRING_TABLE_2 = [["1", "2", "1", "2", "1", "2", "", ""]]
STRING_TABLE_exceeded_output_current = [["2", "2", "2", "1", "2", "2", "", ""]]
STRING_TABLE_no_5V = [["2", "2", "1", "2", "", "2", "2", "2"]]
STRING_TABLE_no_5V_all_crit = [["2", "2", "1", "2", "", "1", "1", "1"]]
STRING_TABLE_not_avail_powersupply = [["2", "2", "2", "2", "2", "0", "", ""]]


@pytest.mark.parametrize(
    "info,expected",
    [
        (
            STRING_TABLE_1,
            Status(
                CommunictionStatus.Established,
                Source.B,
                RedunandancyStatus.Redundant,
                OverCurrentStatus.OK,
                [
                    PowerSource(name="5V", status=PowerSupplyStatus.OK),
                    PowerSource(name="24V", status=PowerSupplyStatus.OK),
                ],
            ),
        ),
        (
            STRING_TABLE_2,
            Status(
                com_status=CommunictionStatus.NeverDiscovered,
                selected_source=Source.B,
                redundancy=RedunandancyStatus.Lost,
                overcurrent=OverCurrentStatus.OK,
                powersources=[
                    PowerSource(name="5V", status=PowerSupplyStatus.Failure),
                    PowerSource(name="24V", status=PowerSupplyStatus.OK),
                ],
            ),
        ),
        (
            STRING_TABLE_no_5V,
            Status(
                com_status=CommunictionStatus.Established,
                selected_source=Source.B,
                redundancy=RedunandancyStatus.Lost,
                overcurrent=OverCurrentStatus.OK,
                powersources=[
                    PowerSource(name="24V", status=PowerSupplyStatus.OK),
                    PowerSource(name="3.3V", status=PowerSupplyStatus.OK),
                    PowerSource(name="1.0V", status=PowerSupplyStatus.OK),
                ],
            ),
        ),
        (
            STRING_TABLE_not_avail_powersupply,
            Status(
                CommunictionStatus.Established,
                Source.B,
                RedunandancyStatus.Redundant,
                OverCurrentStatus.OK,
                [
                    PowerSource(name="5V", status=PowerSupplyStatus.OK),
                    PowerSource(name="24V", status=PowerSupplyStatus.NotAvailable),
                ],
            ),
        ),
    ],
)
def test_parse_apc_ats_status(info: list[list[str]], expected: Status) -> None:
    assert parse_apc_ats_status(info) == expected


@pytest.mark.parametrize(
    "info, expected",
    [
        (STRING_TABLE_1, [Service(parameters={"power_source": 2})]),
        ([[], []], []),
    ],
)
def test_apc_ats_status_discovery(info: list[list[str]], expected: list[Service]) -> None:
    parsed = parse_apc_ats_status(info)
    if not expected:
        assert parsed is None
    else:
        assert list(discover_apc_ats_status(parsed)) == expected  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "info, source, expected",
    [
        pytest.param(
            STRING_TABLE_1,
            {"power_source": 2},
            [
                Result(
                    state=State.OK,
                    summary="Power source B selected",
                ),
                Result(
                    state=State.OK,
                    summary="Device fully redundant",
                ),
            ],
            id="Everything's ok",
        ),
        pytest.param(
            STRING_TABLE_1,
            {"power_source": 1},
            [
                Result(
                    state=State.CRIT,
                    summary="Power source Changed from A to B",
                ),
                Result(
                    state=State.OK,
                    summary="Device fully redundant",
                ),
            ],
            id="Crit due to power source changed with regard to the discovered state",
        ),
        pytest.param(
            STRING_TABLE_2,
            {"power_source": 2},
            [
                Result(
                    state=State.OK,
                    summary="Power source B selected",
                ),
                Result(
                    state=State.WARN,
                    summary="Communication Status: never Discovered",
                ),
                Result(
                    state=State.CRIT,
                    summary="redundancy lost",
                ),
                Result(
                    state=State.CRIT,
                    summary="5V power supply failed",
                ),
            ],
            id="Crit due to communication status, redundancy and 5V power supply",
        ),
        pytest.param(
            STRING_TABLE_exceeded_output_current,
            {"power_source": 2},
            [
                Result(
                    state=State.OK,
                    summary="Power source B selected",
                ),
                Result(
                    state=State.OK,
                    summary="Device fully redundant",
                ),
                Result(
                    state=State.CRIT,
                    summary="exceeded output current threshold",
                ),
            ],
            id="Crit due to exceeded output current",
        ),
        pytest.param(
            STRING_TABLE_no_5V,
            {"power_source": 2},
            [
                Result(
                    state=State.OK,
                    summary="Power source B selected",
                ),
                Result(
                    state=State.CRIT,
                    summary="redundancy lost",
                ),
            ],
            id="No 5V power supply",
        ),
        pytest.param(
            STRING_TABLE_no_5V_all_crit,
            {"power_source": 2},
            [
                Result(
                    state=State.OK,
                    summary="Power source B selected",
                ),
                Result(
                    state=State.CRIT,
                    summary="redundancy lost",
                ),
                Result(
                    state=State.CRIT,
                    summary="24V power supply failed",
                ),
                Result(
                    state=State.CRIT,
                    summary="3.3V power supply failed",
                ),
                Result(
                    state=State.CRIT,
                    summary="1.0V power supply failed",
                ),
            ],
            id="No 5V power supply, all other power supplies are critical",
        ),
        pytest.param(
            STRING_TABLE_not_avail_powersupply,
            {"power_source": 2},
            [
                Result(
                    state=State.OK,
                    summary="Power source B selected",
                ),
                Result(
                    state=State.OK,
                    summary="Device fully redundant",
                ),
                Result(
                    state=State.OK,
                    summary="24V power supply not available",
                ),
            ],
        ),
    ],
)
def test_apc_ats_status_check(
    info: list[list[str]], source: Mapping[str, object], expected: list[Result]
) -> None:
    parsed = parse_apc_ats_status(info)
    assert parsed is not None
    assert list(check_apc_ats_status(source, parsed)) == expected
