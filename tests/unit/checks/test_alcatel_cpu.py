#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from tests.testlib import Check

from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable

pytestmark = pytest.mark.checks

CHECK_NAME = "alcatel_cpu"


@pytest.mark.parametrize(
    "info, result_expected",
    [
        (
            [["doesnt matter", "doesent matter"], ["doesnt matter"]],
            [(None, (90.0, 95.0))],
        ),
    ],
)
def test_inventory_function(info: StringTable, result_expected: Sequence[object]) -> None:
    check = Check(CHECK_NAME)
    result = list(check.run_discovery(info))
    assert result == result_expected


@pytest.mark.parametrize(
    "parameters, info, state_expected, infotext_expected, perfdata_expected",
    [
        ((30, 40), [["29"]], 0, "total: 29.0%", [("util", 29, 30, 40, 0, 100)]),
        (
            (30, 40),
            [["31"]],
            1,
            "total: 31.0% (warn/crit at 30.0%/40.0%)",
            [("util", 31, 30, 40, 0, 100)],
        ),
        (
            (30, 40),
            [["41"]],
            2,
            "total: 41.0% (warn/crit at 30.0%/40.0%)",
            [("util", 41, 30, 40, 0, 100)],
        ),
    ],
)
def test_check_function(
    parameters: tuple[int, int],
    info: StringTable,
    state_expected: int,
    infotext_expected: str,
    perfdata_expected: object,
) -> None:
    """
    Verifies if check function asserts warn and crit CPU levels.
    """
    check = Check(CHECK_NAME)
    item = None
    state, infotext, perfdata = check.run_check(item, parameters, info)
    assert state == state_expected
    assert infotext == infotext_expected
    assert perfdata == perfdata_expected
