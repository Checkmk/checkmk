#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result
from cmk.base.plugins.agent_based.agent_based_api.v1 import State as state
from cmk.base.plugins.agent_based.netscaler_vserver import _check_netscaler_vservers


@pytest.fixture(name="clustered_vservers")
def clustered_vservers_fixture():
    return [
        {
            "entity_service_type": "loadbalancing",
            "health": 75.2,
            "protocol": "ssl",
            "request_rate": 0,
            "rx_bytes": 0,
            "service_state": (0, "up"),
            "socket": "0.0.0.0:0",
            "tx_bytes": 5,
            "node": "node1",
        },
        {
            "entity_service_type": "ssl vpn",
            "protocol": "ssl",
            "request_rate": 1,
            "rx_bytes": 2,
            "service_state": (1, "busy"),
            "socket": "10.101.6.11:443",
            "tx_bytes": 0,
            "node": "node2",
        },
    ]


def test_check_netscaler_vservers_clustered_best(clustered_vservers) -> None:
    assert list(
        _check_netscaler_vservers(
            {
                "health_levels": (100.0, 0.1),
                "cluster_status": "best",
            },
            clustered_vservers,
        )
    ) == [
        Result(state=state.OK, summary="Status: up (node1)"),
        Result(state=state.OK, summary="Status: busy (node2)"),
        Result(
            state=state.WARN,
            summary="Health: 75.20% (warn/crit below 100.00%/0.10%)",
            details="Health: 75.20% (warn/crit below 100.00%/0.10%)",
        ),
        Metric("health_perc", 75.2, boundaries=(0.0, 100.0)),
        Result(
            state=state.OK,
            summary="Type: loadbalancing, Protocol: ssl, Socket: 0.0.0.0:0",
            details="Type: loadbalancing, Protocol: ssl, Socket: 0.0.0.0:0",
        ),
        Result(state=state.OK, summary="Request rate: 1/s"),
        Metric("request_rate", 1.0),
        Result(state=state.OK, summary="In: 16.0 Bit/s"),
        Metric("if_in_octets", 2.0),
        Result(state=state.OK, summary="Out: 40.0 Bit/s"),
        Metric("if_out_octets", 5.0),
    ]


def test_check_netscaler_vservers_clustered_worst(clustered_vservers) -> None:
    clustered_vservers[0]["service_state"] = (
        1,
        "transition to out of service",
    )
    result, *_ = _check_netscaler_vservers(
        {
            "health_levels": (100.0, 0.1),
            "cluster_status": "worst",
        },
        clustered_vservers,
    )
    assert result == Result(
        state=state.WARN,
        summary="Status: transition to out of service (node1)",
        details="Status: transition to out of service (node1)",
    )
