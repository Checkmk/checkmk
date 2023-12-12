#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.legacy_checks.ra32e_power import check_ra32e_power, inventory_ra32e_power

from cmk.agent_based.v1.type_defs import StringTable

from .checktestlib import BasicCheckResult

pytestmark = pytest.mark.checks

RA32E_POWER = "ra32e_power"


@pytest.mark.parametrize("info,result", [([[""]], []), ([["0"]], [(None, {})])])
def test_ra32e_power_discovery(info: StringTable, result: object) -> None:
    assert list(inventory_ra32e_power(info)) == result


def test_ra32e_power_check_battery() -> None:
    result = check_ra32e_power(None, {}, [["0"]])

    assert len(result) == 2
    status, infotext = result
    assert status == 1
    assert "battery" in infotext


def test_ra32e_power_check_acpower() -> None:
    result = BasicCheckResult(*check_ra32e_power(None, {}, [["1"]]))

    assert result.status == 0
    assert "AC/Utility" in result.infotext


def test_ra32e_power_check_nodata() -> None:
    result = BasicCheckResult(*check_ra32e_power(None, {}, [[""]]))

    assert result.status == 3
    assert "unknown" in result.infotext
