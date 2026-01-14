#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import StringTable
from cmk.base.legacy_checks.db2_connections import check_db2_connections, discover_db2_connections
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
            [("db2taddm:CMDBS1", None), ("db2taddm:CMDBS1de", None)],
        ),
    ],
)
def test_discover_db2_connections(
    info: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for db2_connections check."""
    parsed = parse_db2_dbs(info)
    result = list(discover_db2_connections(parsed))
    assert sorted(result) == sorted(expected_discoveries)


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
                (0, "Connections: 40.00", [("connections", 40, 150, 200)]),
                (0, "Port: 50214"),
                (0, "Latency: 1003.00 ms", [("latency", 1003)]),
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
                (0, "Connections: 42.00", [("connections", 42, 150, 200)]),
                (0, "Port: 50213"),
                (0, "Latency: 1003.00 ms", [("latency", 1003)]),
            ],
        ),
    ],
)
def test_check_db2_connections(
    item: str, params: Mapping[str, Any], info: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for db2_connections check."""
    parsed = parse_db2_dbs(info)
    result = list(check_db2_connections(item, params, parsed))
    assert result == expected_results
