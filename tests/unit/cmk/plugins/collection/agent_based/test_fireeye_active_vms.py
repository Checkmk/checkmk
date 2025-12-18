#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.legacy_checks.fireeye_active_vms import (
    check_fireeye_active_vms,
    discover_fireeye_active_vms,
)

SECTION = [["42"]]


def test_discover_nothing() -> None:
    assert not list(discover_fireeye_active_vms([]))


def test_discover_something() -> None:
    assert list(discover_fireeye_active_vms(SECTION)) == [(None, {})]


def test_check_ok() -> None:
    result = list(check_fireeye_active_vms(None, {"vms": (50, 100)}, SECTION))
    assert result == [
        (
            0,
            "Active VMs: 42",
            [("active_vms", 42.0, 50.0, 100.0)],
        )
    ]


def test_check_warn() -> None:
    result = list(check_fireeye_active_vms(None, {"vms": (23, 50)}, SECTION))
    assert result == [
        (
            1,
            "Active VMs: 42 (warn/crit at 23/50)",
            [("active_vms", 42.0, 23.0, 50.0)],
        )
    ]


def test_check_crit() -> None:
    result = list(check_fireeye_active_vms(None, {"vms": (23, 36)}, SECTION))
    assert result == [
        (
            2,
            "Active VMs: 42 (warn/crit at 23/36)",
            [("active_vms", 42.0, 23.0, 36.0)],
        )
    ]
