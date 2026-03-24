#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Result, State
from cmk.plugins.dell.agent_based.dell_compellent_disks import (
    check_dell_compellent_disks,
    discover_dell_compellent_disks,
    parse_dell_compellent_disks,
)

_STRING_TABLE = [
    [
        ["1", "1", "01-01", "1", "", "1"],
        ["2", "999", "01-02", "1", "", "1"],
        ["3", "1", "01-03", "999", "", "1"],
        ["4", "1", "01-04", "2", "ATTENTION", "1"],
        ["5", "1", "01-05", "999", "ATTENTION", "1"],
        ["10", "2", "01-10", "2", "KAPUTT", "1"],
        ["20", "2", "01-20", "0", "INVALID-DISK-STATE", "1"],
    ],
    [
        ["1", "serial1"],
        ["2", "serial2"],
        ["3", "serial3"],
        ["4", "serial4"],
        ["5", "serial5"],
        ["10", "serial10"],
        ["20", "serial20"],
    ],
]


def test_discover_dell_compellent_disks() -> None:
    parsed = parse_dell_compellent_disks(_STRING_TABLE)
    result = list(discover_dell_compellent_disks(parsed))
    assert sorted(s.item for s in result if s.item is not None) == sorted(
        ["01-01", "01-02", "01-03", "01-04", "01-05", "01-10", "01-20"]
    )


@pytest.mark.parametrize(
    "item, expected_results",
    [
        (
            "01-01",
            [
                Result(state=State.OK, summary="Status: UP"),
                Result(state=State.OK, summary="Location: Enclosure 1"),
                Result(state=State.OK, summary="Serial number: serial1"),
                Result(state=State.OK, summary="Health: healthy"),
            ],
        ),
        (
            "01-02",
            [
                Result(state=State.UNKNOWN, summary="Status: unknown[999]"),
                Result(state=State.OK, summary="Location: Enclosure 1"),
                Result(state=State.OK, summary="Serial number: serial2"),
                Result(state=State.OK, summary="Health: healthy"),
            ],
        ),
        (
            "01-03",
            [
                Result(state=State.OK, summary="Status: UP"),
                Result(state=State.OK, summary="Location: Enclosure 1"),
                Result(state=State.OK, summary="Serial number: serial3"),
                Result(
                    state=State.UNKNOWN,
                    summary="Health: unknown, Reason: unknown health state [999]",
                ),
            ],
        ),
        (
            "01-04",
            [
                Result(state=State.OK, summary="Status: UP"),
                Result(state=State.OK, summary="Location: Enclosure 1"),
                Result(state=State.OK, summary="Serial number: serial4"),
                Result(state=State.CRIT, summary="Health: not healthy, Reason: ATTENTION"),
            ],
        ),
        (
            "01-05",
            [
                Result(state=State.OK, summary="Status: UP"),
                Result(state=State.OK, summary="Location: Enclosure 1"),
                Result(state=State.OK, summary="Serial number: serial5"),
                Result(
                    state=State.UNKNOWN,
                    summary="Health: unknown, Reason: ATTENTION, unknown health state [999]",
                ),
            ],
        ),
        (
            "01-10",
            [
                Result(state=State.CRIT, summary="Status: DOWN"),
                Result(state=State.OK, summary="Location: Enclosure 1"),
                Result(state=State.OK, summary="Serial number: serial10"),
                Result(state=State.CRIT, summary="Health: not healthy, Reason: KAPUTT"),
            ],
        ),
        (
            "01-20",
            [
                Result(state=State.CRIT, summary="Status: DOWN"),
                Result(state=State.OK, summary="Location: Enclosure 1"),
                Result(state=State.OK, summary="Serial number: serial20"),
                Result(
                    state=State.UNKNOWN,
                    summary="Health: unknown, Reason: INVALID-DISK-STATE, unknown health state [0]",
                ),
            ],
        ),
    ],
)
def test_check_dell_compellent_disks(
    item: str,
    expected_results: Sequence[Result],
) -> None:
    parsed = parse_dell_compellent_disks(_STRING_TABLE)
    assert list(check_dell_compellent_disks(item, parsed)) == expected_results
