#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]
from testlib import Check  # type: ignore[import]
from checktestlib import BasicCheckResult

pytestmark = pytest.mark.checks

RA32E_POWER = "ra32e_power"


@pytest.mark.parametrize("info,result", [([[u'']], None), ([[u'0']], [(None, {})])])
@pytest.mark.usefixtures("config_load_all_checks")
def test_ra32e_power_discovery(info, result):
    check = Check(RA32E_POWER)
    assert check.run_discovery(info) == result


@pytest.mark.usefixtures("config_load_all_checks")
def test_ra32e_power_check_battery():
    check = Check(RA32E_POWER)
    result = check.run_check(None, {}, [['0']])

    assert len(result) == 2
    status, infotext = result
    assert status == 1
    assert "battery" in infotext


@pytest.mark.usefixtures("config_load_all_checks")
def test_ra32e_power_check_acpower():
    check = Check(RA32E_POWER)
    result = BasicCheckResult(*check.run_check(None, {}, [['1']]))

    assert result.status == 0
    assert 'AC/Utility' in result.infotext


@pytest.mark.usefixtures("config_load_all_checks")
def test_ra32e_power_check_nodata():
    check = Check(RA32E_POWER)
    result = BasicCheckResult(*check.run_check(None, {}, [['']]))

    assert result.status == 3
    assert 'unknown' in result.infotext
