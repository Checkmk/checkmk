#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.testlib import Check

from .checktestlib import BasicCheckResult

pytestmark = pytest.mark.checks

RA32E_POWER = "ra32e_power"


@pytest.mark.parametrize("info,result", [([[""]], None), ([["0"]], [(None, {})])])
def test_ra32e_power_discovery(info, result) -> None:
    check = Check(RA32E_POWER)
    assert check.run_discovery(info) == result


def test_ra32e_power_check_battery() -> None:
    check = Check(RA32E_POWER)
    result = check.run_check(None, {}, [["0"]])

    assert len(result) == 2
    status, infotext = result
    assert status == 1
    assert "battery" in infotext


def test_ra32e_power_check_acpower() -> None:
    check = Check(RA32E_POWER)
    result = BasicCheckResult(*check.run_check(None, {}, [["1"]]))

    assert result.status == 0
    assert "AC/Utility" in result.infotext


def test_ra32e_power_check_nodata() -> None:
    check = Check(RA32E_POWER)
    result = BasicCheckResult(*check.run_check(None, {}, [[""]]))

    assert result.status == 3
    assert "unknown" in result.infotext
