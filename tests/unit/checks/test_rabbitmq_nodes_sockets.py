#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

import pytest

from cmk.base.legacy_checks.rabbitmq_nodes import (
    check_rabbitmq_nodes_sockets,
    discover_key,
    Section,
)


@pytest.mark.parametrize(
    ["section", "expected"],
    [
        pytest.param({}, [], id="no service"),
        pytest.param(
            {
                "rabbit@my-rabbit": {
                    "sockets": {"sockets_used": 0, "sockets_total": 943629},
                }
            },
            [("rabbit@my-rabbit", {})],
            id="service",
        ),
    ],
)
def test_discover_proc(section: Mapping[str, Any], expected: Iterable[tuple[str, Mapping]]) -> None:
    assert list(discover_key("sockets")(section)) == expected


@pytest.mark.parametrize(
    ["item", "params", "section", "expected"],
    [
        pytest.param("rabbit@my-rabbit", {}, {}, None, id="no data"),
        pytest.param(
            "rabbit@my-rabbit",
            {},
            {
                "rabbit@my-rabbit": {
                    "sockets": {"sockets_used": 0},
                }
            },
            None,
            id="partial data (sockets_total missing)",
        ),
        pytest.param(
            "rabbit@my-rabbit",
            {},
            {
                "rabbit@my-rabbit": {
                    "sockets": {"sockets_used": 0},
                }
            },
            None,
            id="partial data (sockets_used missing)",
        ),
        pytest.param(
            "rabbit@my-rabbit",
            {},
            {
                "rabbit@my-rabbit": {
                    "sockets": {"sockets_used": 0, "sockets_total": 943629},
                }
            },
            (
                0,
                "Sockets used: 0 of 943629, 0%",
                [("sockets", 0, None, None, 0, 943629)],
            ),
            id="no levels",
        ),
        pytest.param(
            "rabbit@my-rabbit",
            {"levels": ("fd_abs", (400000, 800000))},
            {
                "rabbit@my-rabbit": {
                    "sockets": {"sockets_used": 471814, "sockets_total": 943629},
                }
            },
            (
                1,
                "Sockets used: 471814 of 943629, 50.00% (warn/crit at 400000/800000)",
                [("sockets", 471814, 400000, 800000, 0, 943629)],
            ),
            id="absolute levels",
        ),
        pytest.param(
            "rabbit@my-rabbit",
            {"levels": ("fd_perc", (50.0, 90.0))},
            {
                "rabbit@my-rabbit": {
                    "sockets": {"sockets_used": 896448, "sockets_total": 943629},
                }
            },
            (
                2,
                "Sockets used: 896448 of 943629, 95.00% (warn/crit at 50.00%/90.00%)",
                [("sockets", 896448, 471814, 849266, 0, 943629)],
            ),
            id="percentage levels",
        ),
    ],
)
def test_check_rabbitmq_nodes_sockets(
    item: str,
    params: Mapping[str, Any],
    section: Section,
    expected: tuple[int, str, Sequence[tuple[str, int, int, int, int, int]]] | None,
) -> None:
    assert check_rabbitmq_nodes_sockets(item, params, section) == expected
