#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest
from freezegun import freeze_time

from tests.testlib import Check

from cmk.base.plugins.agent_based.agent_based_api.v1 import State
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable


@freeze_time("2020-01-13")
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
    status, _description = agent.run_check("1", (13, 14), info)
    assert State(status) == expected_status
