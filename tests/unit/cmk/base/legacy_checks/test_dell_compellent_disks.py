#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v1.type_defs import StringTable
from cmk.base.legacy_checks.dell_compellent_disks import (
    check_dell_compellent_disks,
    discover_dell_compellent_disks,
    parse_dell_compellent_disks,
)


@pytest.mark.parametrize(
    "string_table, expected_discoveries",
    [
        (
            [
                [
                    ["1", "1", "01-01", "1", "", "1"],
                    ["2", "999", "01-02", "1", "", "1"],
                    ["3", "1", "01-03", "999", "", "1"],
                    ["4", "1", "01-04", "0", "ATTENTION", "1"],
                    ["5", "1", "01-05", "999", "ATTENTION", "1"],
                    ["10", "2", "01-10", "0", "KAPUTT", "1"],
                ],
                [
                    ["1", "serial1"],
                    ["2", "serial2"],
                    ["3", "serial3"],
                    ["4", "serial4"],
                    ["5", "serial5"],
                    ["10", "serial10"],
                ],
            ],
            ["01-01", "01-02", "01-03", "01-04", "01-05", "01-10"],
        ),
    ],
)
def test_discover_dell_compellent_disks(
    string_table: StringTable, expected_discoveries: Sequence[tuple[str, Mapping[str, Any]]]
) -> None:
    """Test discovery function for dell_compellent_disks check."""
    parsed = parse_dell_compellent_disks(string_table)
    result = list(discover_dell_compellent_disks(parsed))
    assert sorted([item for item, _ in result]) == sorted(expected_discoveries)


@pytest.mark.parametrize(
    "item, params, string_table, expected_results",
    [
        (
            "01-01",
            {},
            [
                [
                    ["1", "1", "01-01", "1", "", "1"],
                    ["2", "999", "01-02", "1", "", "1"],
                    ["3", "1", "01-03", "999", "", "1"],
                    ["4", "1", "01-04", "0", "ATTENTION", "1"],
                    ["5", "1", "01-05", "999", "ATTENTION", "1"],
                    ["10", "2", "01-10", "0", "KAPUTT", "1"],
                ],
                [
                    ["1", "serial1"],
                    ["2", "serial2"],
                    ["3", "serial3"],
                    ["4", "serial4"],
                    ["5", "serial5"],
                    ["10", "serial10"],
                ],
            ],
            [(0, "Status: UP"), (0, "Location: Enclosure 1"), (0, "Serial number: serial1")],
        ),
        (
            "01-02",
            {},
            [
                [
                    ["1", "1", "01-01", "1", "", "1"],
                    ["2", "999", "01-02", "1", "", "1"],
                    ["3", "1", "01-03", "999", "", "1"],
                    ["4", "1", "01-04", "0", "ATTENTION", "1"],
                    ["5", "1", "01-05", "999", "ATTENTION", "1"],
                    ["10", "2", "01-10", "0", "KAPUTT", "1"],
                ],
                [
                    ["1", "serial1"],
                    ["2", "serial2"],
                    ["3", "serial3"],
                    ["4", "serial4"],
                    ["5", "serial5"],
                    ["10", "serial10"],
                ],
            ],
            [
                (3, "Status: unknown[999]"),
                (0, "Location: Enclosure 1"),
                (0, "Serial number: serial2"),
            ],
        ),
        (
            "01-03",
            {},
            [
                [
                    ["1", "1", "01-01", "1", "", "1"],
                    ["2", "999", "01-02", "1", "", "1"],
                    ["3", "1", "01-03", "999", "", "1"],
                    ["4", "1", "01-04", "0", "ATTENTION", "1"],
                    ["5", "1", "01-05", "999", "ATTENTION", "1"],
                    ["10", "2", "01-10", "0", "KAPUTT", "1"],
                ],
                [
                    ["1", "serial1"],
                    ["2", "serial2"],
                    ["3", "serial3"],
                    ["4", "serial4"],
                    ["5", "serial5"],
                    ["10", "serial10"],
                ],
            ],
            [(0, "Status: UP"), (0, "Location: Enclosure 1"), (0, "Serial number: serial3")],
        ),
        (
            "01-04",
            {},
            [
                [
                    ["1", "1", "01-01", "1", "", "1"],
                    ["2", "999", "01-02", "1", "", "1"],
                    ["3", "1", "01-03", "999", "", "1"],
                    ["4", "1", "01-04", "0", "ATTENTION", "1"],
                    ["5", "1", "01-05", "999", "ATTENTION", "1"],
                    ["10", "2", "01-10", "0", "KAPUTT", "1"],
                ],
                [
                    ["1", "serial1"],
                    ["2", "serial2"],
                    ["3", "serial3"],
                    ["4", "serial4"],
                    ["5", "serial5"],
                    ["10", "serial10"],
                ],
            ],
            [
                (0, "Status: UP"),
                (0, "Location: Enclosure 1"),
                (0, "Serial number: serial4"),
                (2, "Health: not healthy, Reason: ATTENTION"),
            ],
        ),
        (
            "01-05",
            {},
            [
                [
                    ["1", "1", "01-01", "1", "", "1"],
                    ["2", "999", "01-02", "1", "", "1"],
                    ["3", "1", "01-03", "999", "", "1"],
                    ["4", "1", "01-04", "0", "ATTENTION", "1"],
                    ["5", "1", "01-05", "999", "ATTENTION", "1"],
                    ["10", "2", "01-10", "0", "KAPUTT", "1"],
                ],
                [
                    ["1", "serial1"],
                    ["2", "serial2"],
                    ["3", "serial3"],
                    ["4", "serial4"],
                    ["5", "serial5"],
                    ["10", "serial10"],
                ],
            ],
            [
                (0, "Status: UP"),
                (0, "Location: Enclosure 1"),
                (0, "Serial number: serial5"),
                (3, "Health: unknown[999], Reason: ATTENTION"),
            ],
        ),
        (
            "01-10",
            {},
            [
                [
                    ["1", "1", "01-01", "1", "", "1"],
                    ["2", "999", "01-02", "1", "", "1"],
                    ["3", "1", "01-03", "999", "", "1"],
                    ["4", "1", "01-04", "0", "ATTENTION", "1"],
                    ["5", "1", "01-05", "999", "ATTENTION", "1"],
                    ["10", "2", "01-10", "0", "KAPUTT", "1"],
                ],
                [
                    ["1", "serial1"],
                    ["2", "serial2"],
                    ["3", "serial3"],
                    ["4", "serial4"],
                    ["5", "serial5"],
                    ["10", "serial10"],
                ],
            ],
            [
                (2, "Status: DOWN"),
                (0, "Location: Enclosure 1"),
                (0, "Serial number: serial10"),
                (2, "Health: not healthy, Reason: KAPUTT"),
            ],
        ),
    ],
)
def test_check_dell_compellent_disks(
    item: str, params: Mapping[str, Any], string_table: StringTable, expected_results: Sequence[Any]
) -> None:
    """Test check function for dell_compellent_disks check."""
    parsed = parse_dell_compellent_disks(string_table)
    result = list(check_dell_compellent_disks(item, params, parsed))
    assert result == expected_results
