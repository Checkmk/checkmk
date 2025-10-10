#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.base.legacy_checks.qnap_hdd_temp import (
    check_qqnap_hdd_temp,
    discover_qnap_hdd_temp,
    parse_qnap_hdd_temp,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [
                ["HDD1", "37 C/98 F"],
                ["HDD2", "32 C/89 F"],
                ["HDD3", "40 C/104 F"],
                ["HDD4", "39 C/102 F"],
                ["HDD5", "45 C/113 F"],
                ["HDD6", "43 C/109 F"],
            ],
            [("HDD1", {}), ("HDD2", {}), ("HDD3", {}), ("HDD4", {}), ("HDD5", {}), ("HDD6", {})],
        ),
    ],
)
def test_discover_qnap_hdd_temp(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for qnap_hdd_temp check."""
    parsed = parse_qnap_hdd_temp(string_table)
    result = list(discover_qnap_hdd_temp(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "HDD1",
            {"levels": (40, 45)},
            [
                ["HDD1", "37 C/98 F"],
                ["HDD2", "32 C/89 F"],
                ["HDD3", "40 C/104 F"],
                ["HDD4", "39 C/102 F"],
                ["HDD5", "45 C/113 F"],
                ["HDD6", "43 C/109 F"],
            ],
            [(0, "37.0 °C", [("temp", 37.0, 40, 45)])],
        ),
        (
            "HDD2",
            {"levels": (40, 45)},
            [
                ["HDD1", "37 C/98 F"],
                ["HDD2", "32 C/89 F"],
                ["HDD3", "40 C/104 F"],
                ["HDD4", "39 C/102 F"],
                ["HDD5", "45 C/113 F"],
                ["HDD6", "43 C/109 F"],
            ],
            [(0, "32.0 °C", [("temp", 32.0, 40, 45)])],
        ),
        (
            "HDD3",
            {"levels": (40, 45)},
            [
                ["HDD1", "37 C/98 F"],
                ["HDD2", "32 C/89 F"],
                ["HDD3", "40 C/104 F"],
                ["HDD4", "39 C/102 F"],
                ["HDD5", "45 C/113 F"],
                ["HDD6", "43 C/109 F"],
            ],
            [(1, "40.0 °C (warn/crit at 40/45 °C)", [("temp", 40.0, 40, 45)])],
        ),
        (
            "HDD4",
            {"levels": (40, 45)},
            [
                ["HDD1", "37 C/98 F"],
                ["HDD2", "32 C/89 F"],
                ["HDD3", "40 C/104 F"],
                ["HDD4", "39 C/102 F"],
                ["HDD5", "45 C/113 F"],
                ["HDD6", "43 C/109 F"],
            ],
            [(0, "39.0 °C", [("temp", 39.0, 40, 45)])],
        ),
        (
            "HDD5",
            {"levels": (40, 45)},
            [
                ["HDD1", "37 C/98 F"],
                ["HDD2", "32 C/89 F"],
                ["HDD3", "40 C/104 F"],
                ["HDD4", "39 C/102 F"],
                ["HDD5", "45 C/113 F"],
                ["HDD6", "43 C/109 F"],
            ],
            [(2, "45.0 °C (warn/crit at 40/45 °C)", [("temp", 45.0, 40, 45)])],
        ),
        (
            "HDD6",
            {"levels": (40, 45)},
            [
                ["HDD1", "37 C/98 F"],
                ["HDD2", "32 C/89 F"],
                ["HDD3", "40 C/104 F"],
                ["HDD4", "39 C/102 F"],
                ["HDD5", "45 C/113 F"],
                ["HDD6", "43 C/109 F"],
            ],
            [(1, "43.0 °C (warn/crit at 40/45 °C)", [("temp", 43.0, 40, 45)])],
        ),
    ],
)
def test_check_qnap_hdd_temp(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for qnap_hdd_temp check."""
    parsed = parse_qnap_hdd_temp(string_table)
    result = list(check_qqnap_hdd_temp(item, params, parsed))
    assert result == expected_results
