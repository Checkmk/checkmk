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
from cmk.base.legacy_checks.fortigate_memory_base import (
    check_fortigate_memory_base,
    discover_fortigate_memory_base,
    parse_fortigate_memory_base,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        ([["19", "1887424"]], [(None, {})]),
    ],
)
def test_discover_fortigate_memory_base(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for fortigate_memory_base check."""
    parsed = parse_fortigate_memory_base(string_table)
    result = list(discover_fortigate_memory_base(parsed))
    assert sorted(result) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            None,
            (70, 80),
            [["19", "1887424"]],
            (
                0,
                "Used: 19.00% - 350 MiB of 1.80 GiB",
                [("mem_used", 367217213.44, 1352905523.1999998, 1546177740.8000002, 0, 1932722176)],
            ),
        ),
        (
            None,
            {"levels": (15.0, 85.0)},
            [["19", "1887424"]],
            (
                1,
                "Used: 19.00% - 350 MiB of 1.80 GiB (warn/crit at 15.00%/85.00% used)",
                [("mem_used", 367217213.44, 289908326.4, 1642813849.6, 0, 1932722176)],
            ),
        ),
        (
            None,
            {"levels": (-85.0, -15.0)},
            [["19", "1887424"]],
            (
                1,
                "Used: 19.00% - 350 MiB of 1.80 GiB (warn/crit below 85.00%/15.00% free)",
                [("mem_used", 367217213.44, 289908326.4000001, 1642813849.6, 0, 1932722176)],
            ),
        ),
        (
            None,
            {"levels": (340, 1500)},
            [["19", "1887424"]],
            (
                1,
                "Used: 19.00% - 350 MiB of 1.80 GiB (warn/crit at 340 MiB/1.46 GiB used)",
                [("mem_used", 367217213.44, 356515840.0, 1572864000.0, 0, 1932722176)],
            ),
        ),
        (
            None,
            {"levels": (-1717, -1)},
            [["19", "1887424"]],
            (
                1,
                "Used: 19.00% - 350 MiB of 1.80 GiB (warn/crit below 1.68 GiB/1.00 MiB free)",
                [("mem_used", 367217213.44, 132317184.0, 1931673600.0, 0, 1932722176)],
            ),
        ),
    ],
)
def test_check_fortigate_memory_base(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for fortigate_memory_base check."""
    parsed = parse_fortigate_memory_base(string_table)
    result = check_fortigate_memory_base(item, params, parsed)
    assert result == expected_results
