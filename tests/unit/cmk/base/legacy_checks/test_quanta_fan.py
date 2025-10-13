#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.base.check_legacy_includes.quanta import parse_quanta
from cmk.base.legacy_checks.quanta_fan import check_quanta_fan, discover_quanta_fan


@pytest.mark.parametrize(
    "info, expected_discoveries",
    [
        (
            [
                [
                    ["1", "3", "Fan_SYS0_1", "1000", "1500", "800", "-99", "500"],
                    ["2", "3", "Fan_SYS0_2", "1400", "1200", "1000", "-99", "500"],
                    ["4", "3", "Fan_SYS1_2", "9200", "10000", "-99", "-99", "500"],
                    ["5", "3", "Fan_SYS2_1", "11300", "-99", "-99", "1000", "500"],
                    ["6", "3", "Fan_SYS2_2", "1400", "-99", "-99", "2000", "1000"],
                    ["7", "3", "Fan_SYS3_1", "500", "-99", "-99", "2000", "1500"],
                    ["8", "3", "Fan_SYS3_2", "9300", "-99", "-99", "-99", "500"],
                ]
            ],
            [
                ("Fan_SYS0_1", {}),
                ("Fan_SYS0_2", {}),
                ("Fan_SYS1_2", {}),
                ("Fan_SYS2_1", {}),
                ("Fan_SYS2_2", {}),
                ("Fan_SYS3_1", {}),
                ("Fan_SYS3_2", {}),
            ],
        ),
    ],
)
def test_discover_quanta_fan(
    info: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for quanta_fan check."""

    parsed = parse_quanta(info)
    result = list(discover_quanta_fan(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, info, expected_results",
    [
        (
            "Fan_SYS0_1",
            {},
            [
                [
                    ["1", "3", "Fan_SYS0_1", "1000", "1500", "800", "-99", "500"],
                    ["2", "3", "Fan_SYS0_2", "1400", "1200", "1000", "-99", "500"],
                    ["4", "3", "Fan_SYS1_2", "9200", "10000", "-99", "-99", "500"],
                    ["5", "3", "Fan_SYS2_1", "11300", "-99", "-99", "1000", "500"],
                    ["6", "3", "Fan_SYS2_2", "1400", "-99", "-99", "2000", "1000"],
                    ["7", "3", "Fan_SYS3_1", "500", "-99", "-99", "2000", "1500"],
                    ["8", "3", "Fan_SYS3_2", "9300", "-99", "-99", "-99", "500"],
                ]
            ],
            [(0, "Status: OK"), (1, "Speed: 1000 RPM (warn/crit at 800 RPM/1500 RPM)", [])],
        ),
        (
            "Fan_SYS0_2",
            {},
            [
                [
                    ["1", "3", "Fan_SYS0_1", "1000", "1500", "800", "-99", "500"],
                    ["2", "3", "Fan_SYS0_2", "1400", "1200", "1000", "-99", "500"],
                    ["4", "3", "Fan_SYS1_2", "9200", "10000", "-99", "-99", "500"],
                    ["5", "3", "Fan_SYS2_1", "11300", "-99", "-99", "1000", "500"],
                    ["6", "3", "Fan_SYS2_2", "1400", "-99", "-99", "2000", "1000"],
                    ["7", "3", "Fan_SYS3_1", "500", "-99", "-99", "2000", "1500"],
                    ["8", "3", "Fan_SYS3_2", "9300", "-99", "-99", "-99", "500"],
                ]
            ],
            [(0, "Status: OK"), (2, "Speed: 1400 RPM (warn/crit at 1000 RPM/1200 RPM)", [])],
        ),
        (
            "Fan_SYS1_2",
            {},
            [
                [
                    ["1", "3", "Fan_SYS0_1", "1000", "1500", "800", "-99", "500"],
                    ["2", "3", "Fan_SYS0_2", "1400", "1200", "1000", "-99", "500"],
                    ["4", "3", "Fan_SYS1_2", "9200", "10000", "-99", "-99", "500"],
                    ["5", "3", "Fan_SYS2_1", "11300", "-99", "-99", "1000", "500"],
                    ["6", "3", "Fan_SYS2_2", "1400", "-99", "-99", "2000", "1000"],
                    ["7", "3", "Fan_SYS3_1", "500", "-99", "-99", "2000", "1500"],
                    ["8", "3", "Fan_SYS3_2", "9300", "-99", "-99", "-99", "500"],
                ]
            ],
            [(0, "Status: OK"), (0, "Speed: 9200 RPM", [])],
        ),
        (
            "Fan_SYS2_1",
            {},
            [
                [
                    ["1", "3", "Fan_SYS0_1", "1000", "1500", "800", "-99", "500"],
                    ["2", "3", "Fan_SYS0_2", "1400", "1200", "1000", "-99", "500"],
                    ["4", "3", "Fan_SYS1_2", "9200", "10000", "-99", "-99", "500"],
                    ["5", "3", "Fan_SYS2_1", "11300", "-99", "-99", "1000", "500"],
                    ["6", "3", "Fan_SYS2_2", "1400", "-99", "-99", "2000", "1000"],
                    ["7", "3", "Fan_SYS3_1", "500", "-99", "-99", "2000", "1500"],
                    ["8", "3", "Fan_SYS3_2", "9300", "-99", "-99", "-99", "500"],
                ]
            ],
            [(0, "Status: OK"), (0, "Speed: 11300 RPM", [])],
        ),
        (
            "Fan_SYS2_2",
            {},
            [
                [
                    ["1", "3", "Fan_SYS0_1", "1000", "1500", "800", "-99", "500"],
                    ["2", "3", "Fan_SYS0_2", "1400", "1200", "1000", "-99", "500"],
                    ["4", "3", "Fan_SYS1_2", "9200", "10000", "-99", "-99", "500"],
                    ["5", "3", "Fan_SYS2_1", "11300", "-99", "-99", "1000", "500"],
                    ["6", "3", "Fan_SYS2_2", "1400", "-99", "-99", "2000", "1000"],
                    ["7", "3", "Fan_SYS3_1", "500", "-99", "-99", "2000", "1500"],
                    ["8", "3", "Fan_SYS3_2", "9300", "-99", "-99", "-99", "500"],
                ]
            ],
            [(0, "Status: OK"), (1, "Speed: 1400 RPM (warn/crit below 2000 RPM/1000 RPM)", [])],
        ),
        (
            "Fan_SYS3_1",
            {},
            [
                [
                    ["1", "3", "Fan_SYS0_1", "1000", "1500", "800", "-99", "500"],
                    ["2", "3", "Fan_SYS0_2", "1400", "1200", "1000", "-99", "500"],
                    ["4", "3", "Fan_SYS1_2", "9200", "10000", "-99", "-99", "500"],
                    ["5", "3", "Fan_SYS2_1", "11300", "-99", "-99", "1000", "500"],
                    ["6", "3", "Fan_SYS2_2", "1400", "-99", "-99", "2000", "1000"],
                    ["7", "3", "Fan_SYS3_1", "500", "-99", "-99", "2000", "1500"],
                    ["8", "3", "Fan_SYS3_2", "9300", "-99", "-99", "-99", "500"],
                ]
            ],
            [(0, "Status: OK"), (2, "Speed: 500 RPM (warn/crit below 2000 RPM/1500 RPM)", [])],
        ),
        (
            "Fan_SYS3_2",
            {},
            [
                [
                    ["1", "3", "Fan_SYS0_1", "1000", "1500", "800", "-99", "500"],
                    ["2", "3", "Fan_SYS0_2", "1400", "1200", "1000", "-99", "500"],
                    ["4", "3", "Fan_SYS1_2", "9200", "10000", "-99", "-99", "500"],
                    ["5", "3", "Fan_SYS2_1", "11300", "-99", "-99", "1000", "500"],
                    ["6", "3", "Fan_SYS2_2", "1400", "-99", "-99", "2000", "1000"],
                    ["7", "3", "Fan_SYS3_1", "500", "-99", "-99", "2000", "1500"],
                    ["8", "3", "Fan_SYS3_2", "9300", "-99", "-99", "-99", "500"],
                ]
            ],
            [(0, "Status: OK"), (0, "Speed: 9300 RPM", [])],
        ),
    ],
)
def test_check_quanta_fan(
    item: str, params: Mapping[str, Any], info: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for quanta_fan check."""

    parsed = parse_quanta(info)
    result = list(check_quanta_fan(item, params, parsed))
    assert result == expected_results
