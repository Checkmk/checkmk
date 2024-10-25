#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest
import time_machine

from cmk.agent_based.v2 import State, StringTable

from .checktestlib import Check


@time_machine.travel("2020-01-13")
@pytest.mark.parametrize(
    "info, expected_status",
    [
        (
            [["1", "1/13/20"]],
            State.OK,
        ),
        (
            [["1", "01/13/2021"]],
            State.OK,
        ),
        (
            [["1", "12/31/2019"]],
            State.WARN,
        ),
        (
            [["1", "12/30/2019"]],
            State.CRIT,
        ),
        (
            [["1", "Unknown"]],
            State.UNKNOWN,
        ),
    ],
)
def test_check_apc_test(info: StringTable, expected_status: State) -> None:
    """Handle different dates correctly."""
    agent = Check("apc_symmetra_test")
    status, _description = agent.run_check("1", {"levels_elapsed_time": (13, 14)}, info)
    assert State(status) == expected_status
