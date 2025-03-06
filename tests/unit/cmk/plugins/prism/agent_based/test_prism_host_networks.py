#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import json
from collections.abc import Mapping, Sequence
from typing import Any

import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.lib import interfaces
from cmk.plugins.prism.agent_based.prism_host_networks import (
    _check_prism_host_network,
    discovery_prism_host_networks,
    parse_prism_host_networks,
)

RAW = [
    {
        "link_speed_in_kbps": None,
        "mac_address": "0a:0b:0c:0d:0e:0f",
        "name": "eth0",
        "stats": {
            "network.broadcast_received_pkts": "-1",
            "network.broadcast_transmitted_pkts": "-1",
            "network.dropped_received_pkts": "0",
            "network.dropped_transmitted_pkts": "0",
            "network.error_received_pkts": "0",
            "network.error_transmitted_pkts": "0",
            "network.multicast_received_pkts": "-1",
            "network.multicast_transmitted_pkts": "-1",
            "network.received_bytes": "0",
            "network.received_pkts": "0",
            "network.transmitted_bytes": "0",
            "network.transmitted_pkts": "0",
        },
    },
    {
        "link_speed_in_kbps": 10000000,
        "mac_address": "0a:0b:0c:0d:0e:11",
        "name": "eth2",
        "stats": {
            "network.broadcast_received_pkts": "-1",
            "network.broadcast_transmitted_pkts": "-1",
            "network.dropped_received_pkts": "0",
            "network.dropped_transmitted_pkts": "0",
            "network.error_received_pkts": "0",
            "network.error_transmitted_pkts": "0",
            "network.multicast_received_pkts": "-1",
            "network.multicast_transmitted_pkts": "-1",
            "network.received_bytes": "185547077",
            "network.received_pkts": "956968",
            "network.transmitted_bytes": "157213074",
            "network.transmitted_pkts": "135781",
        },
    },
]


@pytest.fixture(name="section", scope="module")
def fixture_section() -> interfaces.Section[interfaces.InterfaceWithRates]:
    return parse_prism_host_networks([[json.dumps(RAW)]])


@pytest.mark.parametrize(
    ["use_empty_section", "expected_discovery_result"],
    [
        pytest.param(
            False,
            [
                Service(
                    item="1",
                    parameters={
                        "item_appearance": "index",
                        "discovered_oper_status": ["1"],
                        "discovered_speed": 10000000000.0,
                    },
                ),
            ],
            id="For every network interface, a Service is discovered.",
        ),
        pytest.param(
            True,
            [],
            id="If there are no items in the input, nothing is discovered.",
        ),
    ],
)
def test_discovery_prism_host_networks(
    use_empty_section: bool,
    expected_discovery_result: Sequence[Service],
    section: interfaces.Section[interfaces.InterfaceWithRates],
) -> None:
    # could not find a way to use a fixture in param
    section = [] if use_empty_section else section
    assert (
        list(discovery_prism_host_networks([(interfaces.DISCOVERY_DEFAULT_PARAMETERS)], section))
        == expected_discovery_result
    )


@pytest.mark.parametrize(
    ["item", "params", "expected_check_result"],
    [
        pytest.param(
            "1",
            {
                "errors": {"both": ("abs", (10, 20))},
                "discovered_speed": 10000000000,
                "discovered_oper_status": ["1"],
            },
            [
                Result(state=State.OK, summary="[eth2]"),
                Result(state=State.OK, summary="(up)", details="Operational state: up"),
                Result(state=State.OK, summary="MAC: 0A:0B:0C:0D:0E:11"),
                Result(state=State.OK, summary="Speed: 10 GBit/s"),
                Result(state=State.OK, summary="In: 6.18 MB/s (0.49%)"),
                Metric("in", 6184902.566666666, boundaries=(0.0, 1250000000.0)),
                Result(state=State.OK, summary="Out: 5.24 MB/s (0.42%)"),
                Metric("out", 5240435.8, boundaries=(0.0, 1250000000.0)),
                Result(state=State.OK, notice="Errors in: 0 packets/s"),
                Metric("inerr", 0.0, levels=(10.0, 20.0)),
                Result(state=State.OK, notice="Discards in: 0 packets/s"),
                Metric("indisc", 0.0),
                Result(state=State.OK, notice="Multicast in: -0.03 packets/s"),
                Metric("inmcast", -0.03333333333333333),
                Result(state=State.OK, notice="Broadcast in: -0.03 packets/s"),
                Metric("inbcast", -0.03333333333333333),
                Result(state=State.OK, notice="Unicast in: 31898.93 packets/s"),
                Metric("inucast", 31898.933333333334),
                Result(state=State.OK, notice="Non-Unicast in: -0.07 packets/s"),
                Metric("innucast", -0.06666666666666667),
                Result(state=State.OK, notice="Errors out: 0 packets/s"),
                Metric("outerr", 0.0, levels=(10.0, 20.0)),
                Result(state=State.OK, notice="Discards out: 0 packets/s"),
                Metric("outdisc", 0.0),
                Result(state=State.OK, notice="Multicast out: -0.03 packets/s"),
                Metric("outmcast", -0.03333333333333333),
                Result(state=State.OK, notice="Broadcast out: -0.03 packets/s"),
                Metric("outbcast", -0.03333333333333333),
                Result(state=State.OK, notice="Unicast out: 4526.03 packets/s"),
                Metric("outucast", 4526.033333333334),
                Result(state=State.OK, notice="Non-Unicast out: -0.07 packets/s"),
                Metric("outnucast", -0.06666666666666667),
            ],
            id="If the network interface is in expected state, the check result is OK.",
        ),
        pytest.param(
            "1",
            {
                "errors": {"both": ("abs", (10, 20))},
                "discovered_speed": 1000000000,
                "discovered_oper_status": ["1"],
            },
            [
                Result(state=State.OK, summary="[eth2]"),
                Result(state=State.OK, summary="(up)", details="Operational state: up"),
                Result(state=State.OK, summary="MAC: 0A:0B:0C:0D:0E:11"),
                Result(state=State.WARN, summary="Speed: 10 GBit/s (expected: 1 GBit/s)"),
                Result(state=State.OK, summary="In: 6.18 MB/s (0.49%)"),
                Metric("in", 6184902.566666666, boundaries=(0.0, 1250000000.0)),
                Result(state=State.OK, summary="Out: 5.24 MB/s (0.42%)"),
                Metric("out", 5240435.8, boundaries=(0.0, 1250000000.0)),
                Result(state=State.OK, notice="Errors in: 0 packets/s"),
                Metric("inerr", 0.0, levels=(10.0, 20.0)),
                Result(state=State.OK, notice="Discards in: 0 packets/s"),
                Metric("indisc", 0.0),
                Result(state=State.OK, notice="Multicast in: -0.03 packets/s"),
                Metric("inmcast", -0.03333333333333333),
                Result(state=State.OK, notice="Broadcast in: -0.03 packets/s"),
                Metric("inbcast", -0.03333333333333333),
                Result(state=State.OK, notice="Unicast in: 31898.93 packets/s"),
                Metric("inucast", 31898.933333333334),
                Result(state=State.OK, notice="Non-Unicast in: -0.07 packets/s"),
                Metric("innucast", -0.06666666666666667),
                Result(state=State.OK, notice="Errors out: 0 packets/s"),
                Metric("outerr", 0.0, levels=(10.0, 20.0)),
                Result(state=State.OK, notice="Discards out: 0 packets/s"),
                Metric("outdisc", 0.0),
                Result(state=State.OK, notice="Multicast out: -0.03 packets/s"),
                Metric("outmcast", -0.03333333333333333),
                Result(state=State.OK, notice="Broadcast out: -0.03 packets/s"),
                Metric("outbcast", -0.03333333333333333),
                Result(state=State.OK, notice="Unicast out: 4526.03 packets/s"),
                Metric("outucast", 4526.033333333334),
                Result(state=State.OK, notice="Non-Unicast out: -0.07 packets/s"),
                Metric("outnucast", -0.06666666666666667),
            ],
            id="If the interface has the wrong speed, the check result is WARN.",
        ),
    ],
)
def test_check_prism_host_networks(
    item: str,
    params: Mapping[str, Any],
    expected_check_result: Sequence[Result],
    section: interfaces.Section[interfaces.InterfaceWithRates],
) -> None:
    assert (
        list(
            _check_prism_host_network(
                item=item,
                params=params,
                section=section,
                value_store={},
            )
        )
        == expected_check_result
    )
