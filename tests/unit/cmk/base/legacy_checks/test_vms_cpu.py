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
from cmk.base.legacy_checks.vms_cpu import check_vms_cpu, discover_vms_cpu, parse_vms_cpu


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        ([["1", "99.17", "0.54", "0.18", "0.00"]], [(None, {})]),
    ],
)
def test_discover_vms_cpu(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for vms_cpu check."""
    parsed = parse_vms_cpu(string_table)
    result = list(discover_vms_cpu(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            None,
            {"iowait": None},
            [["1", "99.17", "0.54", "0.18", "0.00"]],
            [
                (0, "User: 0.54%", [("user", 0.54, None, None)]),
                (0, "System: 0.11%", [("system", 0.10999999999999827, None, None)]),
                (0, "Wait: 0.18%", [("wait", 0.18, None, None)]),
                (0, "Total CPU: 0.83%", [("util", 0.8299999999999983, None, None, 0, 100)]),
                (0, "100% corresponding to: 1 CPU", [("cpu_entitlement", 1, None, None)]),
            ],
        ),
        (
            None,
            {"iowait": (0.1, 0.5)},
            [["1", "99.17", "0.54", "0.18", "0.00"]],
            [
                (0, "User: 0.54%", [("user", 0.54, None, None)]),
                (0, "System: 0.11%", [("system", 0.10999999999999827, None, None)]),
                (1, "Wait: 0.18% (warn/crit at 0.10%/0.50%)", [("wait", 0.18, 0.1, 0.5)]),
                (0, "Total CPU: 0.83%", [("util", 0.8299999999999983, None, None, 0, 100)]),
                (0, "100% corresponding to: 1 CPU", [("cpu_entitlement", 1, None, None)]),
            ],
        ),
    ],
)
def test_check_vms_cpu(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for vms_cpu check."""
    parsed = parse_vms_cpu(string_table)
    result = list(check_vms_cpu(item, params, parsed))
    assert result == expected_results
