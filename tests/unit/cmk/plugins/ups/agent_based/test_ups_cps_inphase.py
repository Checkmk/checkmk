#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.ups.agent_based.ups_cps_inphase import (
    check_ups_cps_inphase,
    discover_ups_cps_inphase,
    parse_ups_cps_inphase,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        ([["32", "NULL"]], [Service(item="1")]),
        ([], []),
    ],
)
def test_discover_ups_cps_inphase(
    string_table: StringTable, expected_discoveries: list[Service]
) -> None:
    assert (
        list(discover_ups_cps_inphase(parse_ups_cps_inphase(string_table) or {}))
        == expected_discoveries
    )


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "1",
            {},
            [["32", "NULL"]],
            [Result(state=State.OK, summary="Voltage: 3.2 V"), Metric("voltage", 3.2)],
        ),
    ],
)
def test_check_ups_cps_inphase(
    item: str,
    params: Mapping[str, object],
    string_table: StringTable,
    expected_results: list[object],
) -> None:
    section = parse_ups_cps_inphase(string_table)
    assert section
    assert list(check_ups_cps_inphase(item, params, section)) == expected_results
