#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.agent_based.v2 import Metric, Result, State, StringTable
from cmk.plugins.collection.agent_based.alcatel_cpu import (
    check_alcatel_cpu,
    inventory_alcatel_cpu,
    parse_alcatel_cpu,
)


def test_discovery_function() -> None:
    assert (parsed := parse_alcatel_cpu([["0"]])) is not None
    assert list(inventory_alcatel_cpu(parsed))


@pytest.mark.parametrize(
    "info, expected",
    [
        (
            [["29"]],
            [
                Result(state=State.OK, summary="Total: 29.00%"),
                Metric("util", 29.0, levels=(90.0, 95.0)),
            ],
        ),
        (
            [["91"]],
            [
                Result(state=State.WARN, summary="Total: 91.00% (warn/crit at 90.00%/95.00%)"),
                Metric("util", 91.0, levels=(90.0, 95.0)),
            ],
        ),
        (
            [["99"]],
            [
                Result(state=State.CRIT, summary="Total: 99.00% (warn/crit at 90.00%/95.00%)"),
                Metric("util", 99.0, levels=(90.0, 95.0)),
            ],
        ),
    ],
)
def test_check_function(info: StringTable, expected: list[Result]) -> None:
    """
    Verifies if check function asserts warn and crit CPU levels.
    """
    assert (parsed := parse_alcatel_cpu(info)) is not None
    assert list(check_alcatel_cpu(parsed)) == expected
