#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import pytest

from cmk.agent_based.legacy.v0_unstable import LegacyCheckResult
from cmk.agent_based.v2 import StringTable
from cmk.base.legacy_checks.juniper_alarm import check_juniper_alarm, inventory_juniper_alarm

STRING_TABLE_UNKNOWN = [["7"], ["2"], ["2"]]
STRING_TABLE_OK = [["2"], ["2"], ["2"]]
STRING_TABLE_CRIT = [["4"], ["2"], ["2"]]


def test_inventory_juniper_alarm() -> None:
    assert list(inventory_juniper_alarm(STRING_TABLE_UNKNOWN)) == [(None, None)]


@pytest.mark.parametrize(
    "info, expected",
    [
        pytest.param(
            STRING_TABLE_UNKNOWN,
            [3, "Status: unhandled alarm type '7'"],
            id="Unknown alarm type",
        ),
        pytest.param(
            STRING_TABLE_OK,
            [0, "Status: OK, good, normally working"],
            id="OK status",
        ),
        pytest.param(
            STRING_TABLE_CRIT,
            [2, "Status: alert, failed, not working (major)"],
            id="Critical status",
        ),
    ],
)
def test_check_juniper_alarm(info: StringTable, expected: LegacyCheckResult) -> None:
    assert list(check_juniper_alarm("", {}, info)) == list(expected)
