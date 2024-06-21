#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import Metric, Result, State
from cmk.plugins.lib.rabbitmq import Section
from cmk.plugins.rabbitmq.agent_based.nodes_proc import check_rabbitmq_nodes_proc


@pytest.mark.parametrize(
    ["item", "params", "section", "expected"],
    [
        pytest.param("rabbit@my-rabbit", {}, {}, [], id="no data"),
        pytest.param(
            "rabbit@my-rabbit",
            {},
            {"proc": {"proc_used": 431}},
            [],
            id="partial data (proc_total missing)",
        ),
        pytest.param(
            "rabbit@my-rabbit",
            {},
            {"proc": {"proc_total": 1048576}},
            [],
            id="partial data (proc_used missing)",
        ),
        pytest.param(
            "rabbit@my-rabbit",
            {},
            {
                "rabbit@my-rabbit": {
                    "proc": {"proc_used": 431, "proc_total": 1048576},
                }
            },
            [
                Result(state=State.OK, summary="Erlang processes used: 431 of 1048576, 0.04%"),
                Metric(name="processes", value=431, boundaries=(0, 1048576)),
            ],
            id="no levels",
        ),
        pytest.param(
            "rabbit@my-rabbit",
            {"levels": ("fd_abs", ("no_levels", None))},
            {
                "rabbit@my-rabbit": {
                    "proc": {"proc_used": 431, "proc_total": 1048576},
                }
            },
            [
                Result(state=State.OK, summary="Erlang processes used: 431 of 1048576, 0.04%"),
                Metric(name="processes", value=431, boundaries=(0, 1048576)),
            ],
            id="(no_levels, None)",
        ),
        pytest.param(
            "rabbit@my-rabbit",
            {"levels": ("fd_abs", ("fixed", (400, 500)))},
            {
                "rabbit@my-rabbit": {
                    "proc": {"proc_used": 431, "proc_total": 1048576},
                }
            },
            [
                Result(
                    state=State.WARN,
                    summary="Erlang processes used: 431 of 1048576, 0.04% (warn/crit at 400/500)",
                ),
                Metric(name="processes", value=431, levels=(400, 500), boundaries=(0, 1048576)),
            ],
            id="absolute levels",
        ),
        pytest.param(
            "rabbit@my-rabbit",
            {"levels": ("fd_perc", ("fixed", (50.0, 90.0)))},
            {
                "rabbit@my-rabbit": {
                    "proc": {"proc_used": 996148, "proc_total": 1048576},
                }
            },
            [
                Result(
                    state=State.CRIT,
                    summary="Erlang processes used: 996148 of 1048576, 95.00% (warn/crit at 50.00%/90.00%)",
                ),
                Metric(
                    name="processes", value=996148, levels=(524288, 943718), boundaries=(0, 1048576)
                ),
            ],
            id="percentage levels",
        ),
    ],
)
def test_check_rabbitmq_nodes_proc(
    item: str,
    params: Mapping[str, Any],
    section: Section,
    expected: Sequence[Result | Metric],
) -> None:
    assert list(check_rabbitmq_nodes_proc(item, params, section)) == expected
