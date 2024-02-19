#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

import pytest

from cmk.base.legacy_checks.rabbitmq_nodes import check_rabbitmq_nodes_proc, discover_key, Section


@pytest.mark.parametrize(
    ["section", "expected"],
    [
        pytest.param({}, [], id="no service"),
        pytest.param(
            {
                "rabbit@my-rabbit": {
                    "proc": {"proc_used": 431, "proc_total": 1048576},
                }
            },
            [("rabbit@my-rabbit", {})],
            id="service",
        ),
    ],
)
def test_discover_proc(section: Mapping[str, Any], expected: Iterable[tuple[str, Mapping]]) -> None:
    assert list(discover_key("proc")(section)) == expected


@pytest.mark.parametrize(
    ["item", "params", "section", "expected"],
    [
        pytest.param("rabbit@my-rabbit", {}, {}, None, id="no data"),
        pytest.param(
            "rabbit@my-rabbit",
            {},
            {"proc": {"proc_used": 431}},
            None,
            id="partial data (proc_total missing)",
        ),
        pytest.param(
            "rabbit@my-rabbit",
            {},
            {"proc": {"proc_total": 1048576}},
            None,
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
            (
                0,
                "Erlang processes used: 431 of 1048576, 0.04%",
                [("processes", 431, None, None, 0, 1048576)],
            ),
            id="no levels",
        ),
        pytest.param(
            "rabbit@my-rabbit",
            {"levels": ("fd_abs", (400, 500))},
            {
                "rabbit@my-rabbit": {
                    "proc": {"proc_used": 431, "proc_total": 1048576},
                }
            },
            (
                1,
                "Erlang processes used: 431 of 1048576, 0.04% (warn/crit at 400/500)",
                [("processes", 431, 400, 500, 0, 1048576)],
            ),
            id="absolute levels",
        ),
        pytest.param(
            "rabbit@my-rabbit",
            {"levels": ("fd_perc", (50.0, 90.0))},
            {
                "rabbit@my-rabbit": {
                    "proc": {"proc_used": 996148, "proc_total": 1048576},
                }
            },
            (
                2,
                "Erlang processes used: 996148 of 1048576, 95.00% (warn/crit at 50.00%/90.00%)",
                [("processes", 996148, 524288, 943718, 0, 1048576)],
            ),
            id="percentage levels",
        ),
    ],
)
def test_check_rabbitmq_nodes_proc(
    item: str,
    params: Mapping[str, Any],
    section: Section,
    expected: tuple[int, str, Sequence[tuple[str, int, int, int, int, int]]] | None,
) -> None:
    assert check_rabbitmq_nodes_proc(item, params, section) == expected
