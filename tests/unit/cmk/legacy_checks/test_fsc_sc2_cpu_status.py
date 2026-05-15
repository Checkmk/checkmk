#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"


import pytest

from cmk.agent_based.v2 import StringTable
from cmk.legacy_checks.fsc_sc2_cpu_status import (
    check_fsc_sc2_cpu_status,
    discover_fsc_sc2_cpu_status,
    parse_fsc_sc2_cpu_status,
)

_SECTION_DISCOVERY: StringTable = [
    ["CPU1", "3", "Xeon Gold", "2400", "16"],
    ["CPU2", "2", "Empty", "0", "0"],
]
_SECTION_OK: StringTable = [["CPU1", "3", "Xeon Gold", "2400", "16"]]
_SECTION_FAILED: StringTable = [["CPU1", "6", "Xeon Gold", "2400", "16"]]
_SECTION_ERROR: StringTable = [["CPU1", "5", "Xeon Gold", "2400", "16"]]


def test_parse_fsc_sc2_cpu_status_is_identity() -> None:
    assert parse_fsc_sc2_cpu_status(_SECTION_DISCOVERY) == _SECTION_DISCOVERY


def test_discover_fsc_sc2_cpu_status_skips_not_present() -> None:
    assert list(discover_fsc_sc2_cpu_status(_SECTION_DISCOVERY)) == [("CPU1", None)]


@pytest.mark.parametrize(
    "section, item, expected",
    [
        pytest.param(
            _SECTION_OK,
            "CPU1",
            (0, "Status is ok, Xeon Gold, 16 cores @ 2400 MHz"),
            id="ok_status",
        ),
        pytest.param(
            _SECTION_FAILED,
            "CPU1",
            (2, "Status is failed, Xeon Gold, 16 cores @ 2400 MHz"),
            id="crit_failed_status",
        ),
        pytest.param(
            _SECTION_ERROR,
            "CPU1",
            (2, "Status is error, Xeon Gold, 16 cores @ 2400 MHz"),
            id="crit_error_status",
        ),
    ],
)
def test_check_fsc_sc2_cpu_status(
    section: StringTable,
    item: str,
    expected: tuple[int, str],
) -> None:
    assert check_fsc_sc2_cpu_status(item, None, section) == expected
