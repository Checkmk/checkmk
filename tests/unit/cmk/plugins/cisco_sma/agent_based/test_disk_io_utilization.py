#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, State, StringTable
from cmk.plugins.cisco_sma.agent_based.disk_io_utilization import (
    check_disk_io_utilization,
    Params,
    parse,
)


def test_parse_for_empty_string_table() -> None:
    assert parse(StringTable([])) is None


def test_parse_for_single_value() -> None:
    assert parse(StringTable([["42"]])) == 42.0


def test_check_disk_io_utilization() -> None:
    assert list(check_disk_io_utilization(Params(upper_levels=("fixed", (10.0, 30.0))), 25.0)) == [
        Result(
            state=State.WARN,
            summary="Total Disk IO Utilization: 25.00% (warn/crit at 10.00%/30.00%)",
        ),
        Metric("disk_io_utilization", 25.0, levels=(10.0, 30.0)),
    ]


def test_check_disk_io_utilization_with_no_limits() -> None:
    assert list(check_disk_io_utilization(Params(upper_levels=("no_levels", None)), 25.0)) == [
        Result(state=State.OK, summary="Total Disk IO Utilization: 25.00%"),
        Metric("disk_io_utilization", 25.0),
    ]
