#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Result, Service, State
from cmk.legacy_checks.ra32e_power import check_ra32e_power, discover_ra32e_power


def test_ra32e_power_discover_nothing() -> None:
    assert not list(discover_ra32e_power([[""]]))


def test_ra32e_power_discover_something() -> None:
    assert list(discover_ra32e_power([["0"]])) == [Service()]


def test_ra32e_power_check_battery() -> None:
    assert list(check_ra32e_power([["0"]])) == [
        Result(state=State.WARN, summary="unit is running on battery backup power")
    ]


def test_ra32e_power_check_acpower() -> None:
    assert list(check_ra32e_power([["1"]])) == [
        Result(state=State.OK, summary="unit is running on AC/Utility power")
    ]


def test_ra32e_power_check_nodata() -> None:
    assert list(check_ra32e_power([[""]])) == [
        Result(state=State.UNKNOWN, summary="unknown status")
    ]
