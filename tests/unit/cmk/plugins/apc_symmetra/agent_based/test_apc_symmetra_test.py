#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping, Sequence
from typing import Any

import pytest
import time_machine

from cmk.agent_based.v2 import Result, State, StringTable
from cmk.plugins.apc_symmetra.agent_based.apc_symmetra_test import check_apc_test


@time_machine.travel("2020-01-13")
@pytest.mark.parametrize(
    "info, params, expected_results",
    [
        pytest.param(
            [["1", "1/13/20"]],
            {"levels_elapsed_time": ("fixed", (13, 14))},
            [
                Result(state=State.OK, summary="Result of self test: OK"),
                Result(state=State.OK, summary="Date of last test: 1/13/20"),
            ],
            id="2-digit year formatting",
        ),
        pytest.param(
            [["1", "01/13/2021"]],
            {"levels_elapsed_time": ("fixed", (13, 14))},
            [
                Result(state=State.OK, summary="Result of self test: OK"),
                Result(state=State.OK, summary="Date of last test: 01/13/2021"),
            ],
            id="ok",
        ),
        pytest.param(
            [["1", "12/31/2019"]],
            {"levels_elapsed_time": ("fixed", (13, 14))},
            [
                Result(
                    state=State.OK,
                    summary="Result of self test: OK",
                ),
                Result(
                    state=State.WARN,
                    summary="Date of last test: 12/31/2019",
                ),
            ],
            id="warn",
        ),
        pytest.param(
            [["1", "12/30/2019"]],
            {"levels_elapsed_time": ("fixed", (13, 14))},
            [
                Result(
                    state=State.OK,
                    summary="Result of self test: OK",
                ),
                Result(
                    state=State.CRIT,
                    summary="Date of last test: 12/30/2019",
                ),
            ],
            id="crit",
        ),
        pytest.param(
            [["1", "Unknown"]],
            {"levels_elapsed_time": ("fixed", (13, 14))},
            [
                Result(
                    state=State.UNKNOWN,
                    summary="Date of last self test is unknown",
                )
            ],
            id="unknown",
        ),
        pytest.param(
            [["1", "12/30/2019"]],
            {},
            [
                Result(state=State.OK, summary="Result of self test: OK"),
                Result(state=State.OK, summary="Date of last test: 12/30/2019"),
            ],
            id="no levels",
        ),
        pytest.param(
            [["1", "12/30/2019"]],
            {"levels_elapsed_time": ("no_levels", None)},
            [
                Result(state=State.OK, summary="Result of self test: OK"),
                Result(state=State.OK, summary="Date of last test: 12/30/2019"),
            ],
            id="no levels configured",
        ),
    ],
)
def test_check_apc_test(
    info: StringTable,
    params: Mapping[str, Any],
    expected_results: Sequence[Result],
) -> None:
    """Handle different dates correctly."""
    assert list(check_apc_test(params, info)) == expected_results
