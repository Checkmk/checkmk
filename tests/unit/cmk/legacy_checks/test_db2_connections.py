#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.legacy_checks.db2_connections import check_db2_connections, discover_db2_connections
from cmk.plugins.db2.agent_based.lib import parse_db2_dbs


@pytest.mark.parametrize(
    "info, expected_discoveries",
    [
        (
            [
                ["[[[db2taddm:CMDBS1]]]"],
                ["port", "50214"],
                ["connections", "40"],
                ["latency", "0:1.03"],
                ["[[[db2taddm:CMDBS1de]]]"],
                ["port", "50213"],
                ["connections", "42"],
                ["latency", "0:1,03"],
            ],
            [Service(item="db2taddm:CMDBS1"), Service(item="db2taddm:CMDBS1de")],
        ),
    ],
)
def test_discover_db2_connections(
    info: StringTable,
    expected_discoveries: Sequence[Service],
) -> None:
    """Test discovery function for db2_connections check."""
    parsed = parse_db2_dbs(info)
    result = list(discover_db2_connections(parsed))
    assert result == list(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, info, expected_results",
    [
        (
            "db2taddm:CMDBS1",
            {"levels_total": (150, 200)},
            [
                ["[[[db2taddm:CMDBS1]]]"],
                ["port", "50214"],
                ["connections", "40"],
                ["latency", "0:1.03"],
                ["[[[db2taddm:CMDBS1de]]]"],
                ["port", "50213"],
                ["connections", "42"],
                ["latency", "0:1,03"],
            ],
            [
                Result(state=State.OK, summary="Connections: 40.00"),
                Metric("connections", 40, levels=(150.0, 200.0)),
                Result(state=State.OK, summary="Port: 50214"),
                Result(state=State.OK, summary="Latency: 1003.00 ms"),
                Metric("latency", 1003),
            ],
        ),
        (
            "db2taddm:CMDBS1de",
            {"levels_total": (150, 200)},
            [
                ["[[[db2taddm:CMDBS1]]]"],
                ["port", "50214"],
                ["connections", "40"],
                ["latency", "0:1.03"],
                ["[[[db2taddm:CMDBS1de]]]"],
                ["port", "50213"],
                ["connections", "42"],
                ["latency", "0:1,03"],
            ],
            [
                Result(state=State.OK, summary="Connections: 42.00"),
                Metric("connections", 42, levels=(150.0, 200.0)),
                Result(state=State.OK, summary="Port: 50213"),
                Result(state=State.OK, summary="Latency: 1003.00 ms"),
                Metric("latency", 1003),
            ],
        ),
    ],
)
def test_check_db2_connections(
    item: str,
    params: Mapping[str, tuple[int, int]],
    info: StringTable,
    expected_results: Sequence[Result | Metric],
) -> None:
    """Test check function for db2_connections check."""
    parsed = parse_db2_dbs(info)
    result = list(check_db2_connections(item, params, parsed))
    assert result == expected_results
