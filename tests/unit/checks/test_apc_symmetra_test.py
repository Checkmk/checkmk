#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping
from typing import Any

import pytest
import time_machine

from cmk.agent_based.v2 import State, StringTable

from .checktestlib import Check


@time_machine.travel("2020-01-13")
@pytest.mark.parametrize(
    "info, params, expected_status, expected_description",
    [
        pytest.param(
            [["1", "1/13/20"]],
            {"levels_elapsed_time": (13, 14)},
            State.OK,
            "Result of self test: OK, Date of last test: 1/13/20",
            id="2-digit year formatting",
        ),
        pytest.param(
            [["1", "01/13/2021"]],
            {"levels_elapsed_time": (13, 14)},
            State.OK,
            "Result of self test: OK, Date of last test: 01/13/2021",
            id="ok",
        ),
        pytest.param(
            [["1", "12/31/2019"]],
            {"levels_elapsed_time": (13, 14)},
            State.WARN,
            "Result of self test: OK, Date of last test: 12/31/2019(!)",
            id="warn",
        ),
        pytest.param(
            [["1", "12/30/2019"]],
            {"levels_elapsed_time": (13, 14)},
            State.CRIT,
            "Result of self test: OK, Date of last test: 12/30/2019(!!)",
            id="crit",
        ),
        pytest.param(
            [["1", "Unknown"]],
            {"levels_elapsed_time": (13, 14)},
            State.UNKNOWN,
            "Date of last self test is unknown",
            id="unknown",
        ),
        pytest.param(
            [["1", "12/30/2019"]],
            {},
            State.OK,
            "Result of self test: OK, Date of last test: 12/30/2019",
            id="no levels",
        ),
    ],
)
def test_check_apc_test(
    info: StringTable, params: Mapping[str, Any], expected_status: State, expected_description: str
) -> None:
    """Handle different dates correctly."""
    agent = Check("apc_symmetra_test")
    status, description = agent.run_check("1", params, info)
    assert State(status) == expected_status
    assert description == expected_description
