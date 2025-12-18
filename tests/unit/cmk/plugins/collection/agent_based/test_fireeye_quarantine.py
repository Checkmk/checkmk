#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.legacy_checks.fireeye_quarantine import (
    check_fireeye_quarantine,
    discover_fireeye_quarantine,
)

SECTION = [["42"]]


def test_discover_nothing() -> None:
    assert not list(discover_fireeye_quarantine([]))


def test_discover_somehting() -> None:
    assert list(discover_fireeye_quarantine(SECTION)) == [(None, {})]


def test_check_ok() -> None:
    result = list(check_fireeye_quarantine(None, {"usage": (50, 100)}, SECTION))
    assert result == [(0, "Usage: 42.00%", [("quarantine", 42.0, 50.0, 100.0)])]


def test_check_warn() -> None:
    result = list(check_fireeye_quarantine(None, {"usage": (23, 50)}, SECTION))
    assert result == [
        (
            1,
            "Usage: 42.00% (warn/crit at 23.00%/50.00%)",
            [("quarantine", 42.0, 23.0, 50.0)],
        )
    ]


def test_check_crit() -> None:
    result = list(check_fireeye_quarantine(None, {"usage": (23, 36)}, SECTION))
    assert result == [
        (
            2,
            "Usage: 42.00% (warn/crit at 23.00%/36.00%)",
            [("quarantine", 42.0, 23.0, 36.0)],
        )
    ]
