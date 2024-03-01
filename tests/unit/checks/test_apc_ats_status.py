#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib import Check

STRING_TABLE_1 = [["2", "2", "2", "2", "2", "2"]]
STRING_TABLE_2 = [["1", "2", "1", "2", "1", "2"]]
STRING_TABLE_exceeded_output_current = [["2", "2", "2", "1", "2", "2"]]
CHECK = "apc_ats_status"


@pytest.mark.parametrize(
    "info, expected",
    [
        (STRING_TABLE_1, [(None, {"power_source": 2})]),
        ([[], []], []),
    ],
)
def test_apc_ats_status_discovery(info, expected):
    assert list(Check(CHECK).run_discovery(info)) == expected


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
    ],
)
def test_apc_ats_status_check(info, source, expected):
    assert Check(CHECK).run_check("no_item", source, info) == expected
