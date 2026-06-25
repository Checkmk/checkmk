#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.ups.agent_based.ups_socomec_out_source import (
    check_ups_socomec_out_source,
    discover_ups_socomec_out_source,
    parse_ups_socomec_out_source,
)


@pytest.mark.parametrize(
    "string_table, expected",
    [
        ([["3"]], [Service()]),
        ([], []),
    ],
)
def test_discover_ups_socomec_out_source(
    string_table: StringTable, expected: list[Service]
) -> None:
    assert (
        list(discover_ups_socomec_out_source(parse_ups_socomec_out_source(string_table)))
        == expected
    )


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("3", Result(state=State.OK, summary="On mains")),
        ("2", Result(state=State.CRIT, summary="On inverter")),
        ("5", Result(state=State.WARN, summary="On bypass")),
        ("1", Result(state=State.UNKNOWN, summary="Unknown")),
    ],
)
def test_check_ups_socomec_out_source(raw: str, expected: Result) -> None:
    assert list(check_ups_socomec_out_source([[raw]])) == [expected]
