#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

import pytest

from cmk.agent_based.v2 import CheckResult, DiscoveryResult, Metric, Result, Service, State
from cmk.plugins.lib.rabbitmq import Section
from cmk.plugins.rabbitmq.agent_based.nodes_sockets import (
    check_rabbitmq_nodes_sockets,
    discover_rabbitmq_nodes_sockets,
    Params,
)


@pytest.mark.parametrize(
    ["section_nodes", "section_cluster", "expected"],
    [
        pytest.param({}, {}, [], id="no service"),
        pytest.param(
            {
                "rabbit@my-rabbit": {
                    "sockets": {"sockets_used": 0, "sockets_total": 943629},
                }
            },
            {"info": {"rabbitmq_version": "3.8.0"}},
            [Service(item="rabbit@my-rabbit")],
            id="service",
        ),
        pytest.param(
            {
                "rabbit@my-rabbit": {
                    "sockets": {"sockets_used": 0, "sockets_total": 0},
                }
            },
            {"info": {"rabbitmq_version": "4.0.1"}},
            [],
            id="no service for RMQ >= 4.0.1",
        ),
    ],
)
def test_discover_sockets(
    section_nodes: Mapping[str, Any], section_cluster: Mapping[str, Any], expected: DiscoveryResult
) -> None:
    assert list(discover_rabbitmq_nodes_sockets(section_nodes, section_cluster)) == expected


@pytest.mark.parametrize(
    ["item", "params", "section_nodes", "section_cluster", "expected"],
    [
        pytest.param("rabbit@my-rabbit", {}, {}, {}, [], id="no data"),
        pytest.param(
            "rabbit@my-rabbit",
            {},
            {
                "rabbit@my-rabbit": {
                    "sockets": {"sockets_used": 0},
                }
            },
            {"info": {"rabbitmq_version": "3.8.0"}},
            [],
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
            {"info": {"rabbitmq_version": "3.8.0"}},
            [],
            id="partial data (sockets_used missing)",
        ),
        pytest.param(
            "rabbit@my-rabbit",
            {},
            {
                "rabbit@my-rabbit": {
                    "sockets": {"sockets_used": 0, "sockets_total": 0},
                }
            },
            {"info": {"rabbitmq_version": "4.0.1"}},
            [Result(state=State.CRIT, summary="No available sockets")],
            id="sockets_total 0",
        ),
        pytest.param(
            "rabbit@my-rabbit",
            {},
            {
                "rabbit@my-rabbit": {
                    "sockets": {"sockets_used": 0, "sockets_total": 943629},
                }
            },
            {"info": {"rabbitmq_version": "3.8.0"}},
            [
                Result(state=State.OK, summary="Sockets used: 0 of 943629, 0%"),
                Metric(name="sockets", value=0, boundaries=(0.0, 943629.0)),
            ],
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
            {"info": {"rabbitmq_version": "3.8.0"}},
            [
                Result(
                    state=State.WARN,
                    summary="Sockets used: 471814 of 943629, 50.00% (warn/crit at 400000/800000)",
                ),
                Metric(
                    name="sockets",
                    value=471814,
                    levels=(400000, 800000),
                    boundaries=(0.0, 943629.0),
                ),
            ],
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
            {"info": {"rabbitmq_version": "3.8.0"}},
            [
                Result(
                    state=State.CRIT,
                    summary="Sockets used: 896448 of 943629, 95.00% (warn/crit at 50.00%/90.00%)",
                ),
                Metric(
                    name="sockets",
                    value=896448,
                    levels=(471814, 849266),
                    boundaries=(0.0, 943629.0),
                ),
            ],
            id="percentage levels CRIT",
        ),
    ],
)
def test_check_rabbitmq_nodes_sockets(
    item: str,
    params: Params,
    section_nodes: Section,
    section_cluster: Section,
    expected: CheckResult,
) -> None:
    assert (
        list(check_rabbitmq_nodes_sockets(item, params, section_nodes, section_cluster)) == expected
    )
