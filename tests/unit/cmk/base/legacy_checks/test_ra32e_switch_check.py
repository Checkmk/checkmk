#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import StringTable
from cmk.base.legacy_checks.ra32e_switch import (
    check_ra32e_switch,
    discover_ra32e_switch,
    parse_ra32e_switch,
)


@pytest.mark.parametrize(
    "info,result",
    [
        (
            [
                [
                    "1",
                    "1",
                    "0",
                    "0",
                    "0",
                    "0",
                    "0",
                    "0",
                    "0",
                    "0",
                    "0",
                    "0",
                    "0",
                    "0",
                    "0",
                    "0",
                ]
            ],
            [
                ("Sensor 01", None),
                ("Sensor 02", None),
                ("Sensor 03", None),
                ("Sensor 04", None),
                ("Sensor 05", None),
                ("Sensor 06", None),
                ("Sensor 07", None),
                ("Sensor 08", None),
                ("Sensor 09", None),
                ("Sensor 10", None),
                ("Sensor 11", None),
                ("Sensor 12", None),
                ("Sensor 13", None),
                ("Sensor 14", None),
                ("Sensor 15", None),
                ("Sensor 16", None),
            ],
        )
    ],
)
def test_ra32e_switch_discovery(info: StringTable, result: Sequence[tuple[str, None]]) -> None:
    assert list(discover_ra32e_switch(parse_ra32e_switch(info))) == result


def test_ra32e_switch_check_closed_no_rule() -> None:
    state, summary, *_rest = check_ra32e_switch("Sensor 01", {"state": "ignore"}, [["1"]])

    assert state == 0
    assert summary.startswith("closed")


def test_ra32e_switch_check_open_expected_close() -> None:
    state, summary, *_rest = check_ra32e_switch(
        "Sensor 03",
        {"state": "closed"},
        [["1", "1", "0", "1", "1", "1", "1", "1", "1", "1", "1", "1", "1", "1", "1", "1"]],
    )

    assert state == 2
    assert summary.startswith("open")
    assert "expected closed" in summary


def test_ra32e_switch_check_no_input() -> None:
    state, summary, *_rest = check_ra32e_switch("Sensor 01", {"state": "ignore"}, [[""]])

    assert state == 3
