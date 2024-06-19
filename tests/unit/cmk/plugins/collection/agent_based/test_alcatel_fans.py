#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

import pytest

from cmk.agent_based.v2 import Result, Service, State, StringTable
from cmk.plugins.collection.agent_based.alcatel_fans import (
    check_alcatel_fans,
    discover_alcatel_fans,
    parse_alcatel_fans,
)


@pytest.mark.parametrize(
    "info, expected",
    [
        ([["doesnt matter"]], [Service(item="1")]),
        (
            [["doesnt matter", "doesent matter"], ["doesnt matter"]],
            [Service(item="1"), Service(item="2")],
        ),
    ],
)
def test_inventory_function(info: StringTable, expected: Sequence[Service]) -> None:
    assert list(discover_alcatel_fans(parse_alcatel_fans(info))) == expected


@pytest.mark.parametrize(
    "item, info, expected",
    [
        ("1", [["0"]], [Result(state=State.CRIT, summary="Fan has no status")]),
        ("1", [["1"]], [Result(state=State.CRIT, summary="Fan not running")]),
        ("1", [["2"]], [Result(state=State.OK, summary="Fan running")]),
    ],
)
def test_check_function(item: str, info: StringTable, expected: Sequence[Result]) -> None:
    """
    Verifies if check function asserts warn and crit Board and CPU temperature levels.
    """
    assert list(check_alcatel_fans(item, parse_alcatel_fans(info))) == expected
