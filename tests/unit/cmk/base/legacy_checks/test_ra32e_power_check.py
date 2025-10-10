#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"


from cmk.agent_based.v2 import Service
from cmk.base.legacy_checks.ra32e_power import check_ra32e_power, discover_ra32e_power


def test_ra32e_power_discover_nothing() -> None:
    assert not list(discover_ra32e_power([[""]]))


def test_ra32e_power_discover_something() -> None:
    assert list(discover_ra32e_power([["0"]])) == [Service()]


def test_ra32e_power_check_battery() -> None:
    state, summary = check_ra32e_power(None, {}, [["0"]])

    assert state == 1
    assert "battery" in summary


def test_ra32e_power_check_acpower() -> None:
    state, summary, *_rest = check_ra32e_power(None, {}, [["1"]])

    assert state == 0
    assert "AC/Utility" in summary


def test_ra32e_power_check_nodata() -> None:
    state, summary, *_rest = check_ra32e_power(None, {}, [[""]])

    assert state == 3
    assert "unknown" in summary
