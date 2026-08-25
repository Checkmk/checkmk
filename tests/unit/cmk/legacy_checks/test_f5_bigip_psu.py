#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.legacy_checks.f5_bigip_psu import (
    check_f5_bigip_psu,
    discover_f5_bigip_psu,
    parse_f5_bigip_psu,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        pytest.param(
            [["1", "1"], ["2", "1"]],
            [Service(item="1"), Service(item="2")],
            id="all present",
        ),
        pytest.param(
            [["1", "1"], ["2", "2"], ["3", "0"]],
            [Service(item="1"), Service(item="3")],
            id="notpresent PSU is skipped",
        ),
    ],
)
def test_discover_f5_bigip_psu(
    string_table: StringTable, expected_discoveries: Sequence[Service]
) -> None:
    """Test discovery function for f5_bigip_psu check."""
    section = parse_f5_bigip_psu(string_table)
    assert list(discover_f5_bigip_psu(section)) == expected_discoveries


@pytest.mark.parametrize(
    "item, string_table, expected_results",
    [
        pytest.param(
            "1",
            [["1", "1"], ["2", "1"]],
            [Result(state=State.OK, summary="PSU state: good")],
            id="good",
        ),
        pytest.param(
            "2",
            [["1", "1"], ["2", "0"]],
            [Result(state=State.CRIT, summary="PSU state: bad!!")],
            id="bad",
        ),
        pytest.param(
            "2",
            [["1", "1"], ["2", "2"]],
            [Result(state=State.WARN, summary="PSU state: notpresent!")],
            id="notpresent",
        ),
        pytest.param(
            "2",
            [["1", "1"], ["2", "3"]],
            [Result(state=State.UNKNOWN, summary="PSU state is unknown")],
            id="unexpected status",
        ),
        pytest.param(
            "3",
            [["1", "1"], ["2", "1"]],
            [],
            id="unknown item",
        ),
    ],
)
def test_check_f5_bigip_psu(
    item: str,
    string_table: StringTable,
    expected_results: Sequence[Result],
) -> None:
    """Test check function for f5_bigip_psu check."""
    section = parse_f5_bigip_psu(string_table)
    assert list(check_f5_bigip_psu(item, section)) == expected_results
