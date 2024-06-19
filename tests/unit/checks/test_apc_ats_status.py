#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.check_legacy_includes.apc_ats import (
    CommunictionStatus,
    OverCurrentStatus,
    PowerSource,
    PowerSupplyStatus,
    RedunandancyStatus,
    Source,
    Status,
)

from .checktestlib import Check

STRING_TABLE_1 = [["2", "2", "2", "2", "2", "2", "", ""]]
STRING_TABLE_2 = [["1", "2", "1", "2", "1", "2", "", ""]]
STRING_TABLE_exceeded_output_current = [["2", "2", "2", "1", "2", "2", "", ""]]
STRING_TABLE_no_5V = [["2", "2", "1", "2", "", "2", "2", "2"]]
STRING_TABLE_no_5V_all_crit = [["2", "2", "1", "2", "", "1", "1", "1"]]
CHECK = "apc_ats_status"


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
    ],
)
def test_parse_apc_ats_status(info, expected):
    assert Check(CHECK).run_parse(info) == expected


@pytest.mark.parametrize(
    "info, expected",
    [
        (STRING_TABLE_1, [(None, {"power_source": 2})]),
        ([[], []], []),
    ],
)
def test_apc_ats_status_discovery(info, expected):
    check = Check(CHECK)
    assert list(check.run_discovery(check.run_parse(info))) == expected


@pytest.mark.parametrize(
    "info, source, expected",
    [
        pytest.param(
            STRING_TABLE_1,
            {"power_source": 2},
            (
                0,
                "Power source B selected, Device fully redundant",
            ),
            id="Everything's ok",
        ),
        pytest.param(
            STRING_TABLE_1,
            {"power_source": 1},
            (
                2,
                "Power source Changed from A to B(!!), Device fully redundant",
            ),
            id="Crit due to power source changed with regard to the discovered state",
        ),
        pytest.param(
            STRING_TABLE_2,
            {"power_source": 2},
            (
                2,
                "Power source B selected, Communication Status: never Discovered(!), "
                "redundancy lost(!!), 5V power supply failed(!!)",
            ),
            id="Crit due to communication status, redundancy and 5V power supply",
        ),
        pytest.param(
            STRING_TABLE_exceeded_output_current,
            {"power_source": 2},
            (
                2,
                "Power source B selected, Device fully redundant, exceeded ouput current "
                "threshold(!!)",
            ),
            id="Crit due to exceeded output current",
        ),
        pytest.param(
            STRING_TABLE_no_5V,
            {"power_source": 2},
            (
                2,
                "Power source B selected, redundancy lost(!!)",
            ),
            id="No 5V power supply",
        ),
        pytest.param(
            STRING_TABLE_no_5V_all_crit,
            {"power_source": 2},
            (
                2,
                "Power source B selected, redundancy lost(!!), 24V power supply failed(!!), "
                "3.3V power supply failed(!!), 1.0V power supply failed(!!)",
            ),
            id="No 5V power supply, all other power supplies are critical",
        ),
    ],
)
def test_apc_ats_status_check(info, source, expected):
    check = Check(CHECK)
    assert check.run_check("no_item", source, check.run_parse(info)) == expected
