#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-def"

from collections.abc import Mapping

import pytest

from cmk.agent_based.v2 import StringTable

from .checktestlib import Check

pytestmark = pytest.mark.checks


@pytest.mark.parametrize(
    "info, item_expected, data_expected",
    [
        ([["29", "0"]], "Board", {}),
        ([["0", "29"]], "CPU", {}),
    ],
)
def test_discover_function(
    info: StringTable, item_expected: str, data_expected: Mapping[object, object]
) -> None:
    """
    Verifies if the item is detected corresponding to info content.
    """
    check = Check("alcatel_temp")
    result = list(check.run_discovery(info))
    assert result[0][0] == item_expected
    assert result[0][1] == data_expected


@pytest.mark.parametrize(
    "parameters, item, info, state_expected, infotext_expected, perfdata_expected",
    [
        ((30, 40), "Slot 1 Board", [["29", "0"]], 0, "29", [("temp", 29, 30, 40)]),
        ((30, 40), "Slot 1 Board", [["31", "0"]], 1, "31", [("temp", 31, 30, 40)]),
        ((30, 40), "Slot 1 Board", [["41", "0"]], 2, "41", [("temp", 41, 30, 40)]),
        ((30, 40), "Slot 1 CPU", [["0", "29"]], 0, "29", [("temp", 29, 30, 40)]),
        ((30, 40), "Slot 1 CPU", [["0", "31"]], 1, "31", [("temp", 31, 30, 40)]),
        ((30, 40), "Slot 1 CPU", [["0", "41"]], 2, "41", [("temp", 41, 30, 40)]),
    ],
)
def test_check_function(
    parameters, item, info, state_expected, infotext_expected, perfdata_expected
):
    """
    Verifies if check function asserts warn and crit Board and CPU temperature levels.
    """
    check = Check("alcatel_temp")
    state, infotext, perfdata = check.run_check(item, parameters, info)
    assert state == state_expected
    assert infotext_expected in infotext
    assert perfdata == perfdata_expected
