#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import copy
from typing import Mapping

import pytest

from cmk.base.plugins.agent_based import lnx_if
from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    Attributes,
    IgnoreResultsError,
    Result,
    Service,
)
from cmk.base.plugins.agent_based.agent_based_api.v1 import State as state
from cmk.base.plugins.agent_based.agent_based_api.v1 import TableRow
from cmk.base.plugins.agent_based.utils import bonding, interfaces


@pytest.mark.parametrize(
    "string_table, result",
    [
        (
            [
                ["[start_iplink]"],
                [
                    "1:",
                    "wlp3s0:",
                    "<BROADCAST,MULTICAST>",
                    "mtu",
                    "1500",
                    "qdisc",
                    "fq_codel",
                    "state",
                    "UP",
                    "mode",
                    "DORMANT",
                    "group",
                    "default",
                    "qlen",
                    "1000",
                ],
                ["link/ether", "AA:AA:AA:AA:AA:AA", "brd", "BB:BB:BB:BB:BB:BB"],
                ["[end_iplink]"],
                ["wlp3s0", "130923553 201184 0 0 0 0 0 16078 23586281 142684 0 0 0 0 0 0"],
            ],
            [
                "1",
                "wlp3s0",
                "wlp3s0",
                "6",
                0,
                "2",
                130923553,
                217262,
                16078,
                0,
                0,
                0,
                23586281,
                142684,
                0,
                0,
                0,
                0,
                0,
                "\xaa\xaa\xaa\xaa\xaa\xaa",
            ],
        ),
        (
            [
                ["[start_iplink]"],
                [
                    "1:",
                    "wlp3s0:",
                    "<BROADCAST,MULTICAST,UP>",
                    "mtu",
                    "1500",
                    "qdisc",
                    "fq_codel",
                    "state",
                    "UP",
                    "mode",
                    "DORMANT",
                    "group",
                    "default",
                    "qlen",
                    "1000",
                ],
                ["link/ether", "BB:BB:BB:BB:BB:BB", "brd", "BB:BB:BB:BB:BB:BB"],
                ["[end_iplink]"],
                ["wlp3s0", "130923553 201184 0 0 0 0 0 16078 23586281 142684 0 0 0 0 0 0"],
            ],
            [
                "1",
                "wlp3s0",
                "wlp3s0",
                "6",
                0,
                "2",
                130923553,
                217262,
                16078,
                0,
                0,
                0,
                23586281,
                142684,
                0,
                0,
                0,
                0,
                0,
                "\xbb\xbb\xbb\xbb\xbb\xbb",
            ],
        ),
        (
            [
                ["[start_iplink]"],
                [
                    "1:",
                    "wlp3s0:",
                    "<BROADCAST,MULTICAST,UP,LOWER_UP>",
                    "mtu",
                    "1500",
                    "qdisc",
                    "fq_codel",
                    "state",
                    "UP",
                    "mode",
                    "DORMANT",
                    "group",
                    "default",
                    "qlen",
                    "1000",
                ],
                ["link/ether", "BB:BB:BB:BB:BB:BB", "brd", "BB:BB:BB:BB:BB:BB"],
                ["[end_iplink]"],
                ["wlp3s0", "130923553 201184 0 0 0 0 0 16078 23586281 142684 0 0 0 0 0 0"],
            ],
            [
                "1",
                "wlp3s0",
                "wlp3s0",
                "6",
                0,
                "1",
                130923553,
                217262,
                16078,
                0,
                0,
                0,
                23586281,
                142684,
                0,
                0,
                0,
                0,
                0,
                "\xbb\xbb\xbb\xbb\xbb\xbb",
            ],
        ),
    ],
)
def test_parse_lnx_if(string_table, result) -> None:
    assert lnx_if.parse_lnx_if(string_table)[0][0] == interfaces.Interface(*result)


INTERFACE = interfaces.Interface(
    "1",
    "wlp3s0",
    "wlp3s0",
    "6",
    0,
    "1",
    130923553,
    217262,
    16078,
    0,
    0,
    0,
    23586281,
    142684,
    0,
    0,
    0,
    0,
    0,
    "\xaa\xaa\xaa\xaa\xaa\xaa",
)

PARAMS = {
    "errors": {"both": ("abs", (10, 20))},
    "speed": 10000000,
    "traffic": [("both", ("upper", ("perc", (5.0, 20.0))))],
    "state": ["1"],
}


def test_check_lnx_if(monkeypatch) -> None:
    section_if = [INTERFACE]
    section: lnx_if.Section = (section_if, {})
    monkeypatch.setattr("time.time", lambda: 0)
    with pytest.raises(IgnoreResultsError):
        list(
            lnx_if.check_lnx_if(
                INTERFACE.index,
                PARAMS,
                section,
                None,
            )
        )
    monkeypatch.setattr("time.time", lambda: 1)
    result_lnx_if = list(
        lnx_if.check_lnx_if(
            INTERFACE.index,
            PARAMS,
            section,
            None,
        )
    )
    monkeypatch.setattr("time.time", lambda: 2)
    result_interfaces = list(
        interfaces.check_multiple_interfaces(
            INTERFACE.index,
            PARAMS,
            section_if,
        )
    )
    assert result_lnx_if == result_interfaces


def test_cluster_check_lnx_if(monkeypatch) -> None:
    section: dict[str, lnx_if.Section] = {}
    ifaces = []
    for i in range(3):
        iface = copy.copy(INTERFACE)
        iface.node = "node%s" % i
        ifaces_node = [iface] * (i + 1)
        section[iface.node] = ifaces_node, {}
        ifaces += ifaces_node
    monkeypatch.setattr("time.time", lambda: 0)
    with pytest.raises(IgnoreResultsError):
        list(
            lnx_if.cluster_check_lnx_if(
                INTERFACE.index,
                PARAMS,
                section,
                {},
            )
        )
    monkeypatch.setattr("time.time", lambda: 1)
    result_lnx_if = list(
        lnx_if.cluster_check_lnx_if(
            INTERFACE.index,
            PARAMS,
            section,
            {},
        )
    )
    monkeypatch.setattr("time.time", lambda: 2)
    result_interfaces = list(
        interfaces.check_multiple_interfaces(
            INTERFACE.index,
            PARAMS,
            ifaces,
        )
    )
    assert result_lnx_if == result_interfaces


@pytest.mark.parametrize(
    "string_table, discovery_results, items_params_results",
    [
        (
            [
                ["[start_iplink]"],
                [
                    "1:",
                    "lo:",
                    "<LOOPBACK,UP,LOWER_UP>",
                    "mtu",
                    "65536",
                    "qdisc",
                    "noqueue",
                    "state",
                    "UNKNOWN",
                    "mode",
                    "DEFAULT",
                    "group",
                    "default",
                    "qlen",
                    "1000",
                ],
                ["link/loopback", "00:00:00:00:00:00", "brd", "00:00:00:00:00:00"],
                [
                    "2:",
                    "wlp3s0:",
                    "<BROADCAST,MULTICAST,UP,LOWER_UP>",
                    "mtu",
                    "1500",
                    "qdisc",
                    "fq_codel",
                    "state",
                    "UP",
                    "mode",
                    "DORMANT",
                    "group",
                    "default",
                    "qlen",
                    "1000",
                ],
                ["link/ether", "AA:AA:AA:AA:AA:BB", "brd", "BB:BB:BB:BB:BB:BB"],
                [
                    "3:",
                    "docker0:",
                    "<BROADCAST,MULTICAST,UP,LOWER_UP>",
                    "mtu",
                    "1500",
                    "qdisc",
                    "noqueue",
                    "state",
                    "UP",
                    "mode",
                    "DEFAULT",
                    "group",
                    "default",
                ],
                ["link/ether", "AA:AA:AA:AA:AA:AA", "brd", "BB:BB:BB:BB:BB:BB"],
                [
                    "5:",
                    "veth6a06585@if4:",
                    "<BROADCAST,MULTICAST,UP,LOWER_UP>",
                    "mtu",
                    "1500",
                    "qdisc",
                    "noqueue",
                    "master",
                    "docker0",
                    "state",
                    "UP",
                    "mode",
                    "DEFAULT",
                    "group",
                    "default",
                ],
                [
                    "link/ether",
                    "AA:AA:AA:AA:AA:AA",
                    "brd",
                    "BB:BB:BB:BB:BB:BB",
                    "link-netnsid",
                    "0",
                ],
                ["[end_iplink]"],
                [
                    "lo",
                    " 164379850  259656    0    0    0     0          0         0 164379850  259656    0    0    0     0       0          0",
                ],
                [
                    "wlp3s0",
                    " 130923553  201184    0    0    0     0          0     16078 23586281  142684    0    0    0     0       0          0",
                ],
                [
                    "docker0",
                    "       0       0    0    0    0     0          0         0    16250     184    0    0    0     0       0          0",
                ],
                [
                    "veth6a06585",
                    "       0       0    0    0    0     0          0         0    25963     287    0    0    0     0       0          0",
                ],
            ],
            [
                Service(
                    item="1", parameters={"discovered_oper_status": ["1"], "discovered_speed": 0}
                ),
                Service(
                    item="4", parameters={"discovered_oper_status": ["1"], "discovered_speed": 0}
                ),
            ],
            [
                (
                    "1",
                    {"errors": {"both": ("abs", (10, 20))}, "speed": 0, "state": ["1"]},
                    [
                        Result(state=state.OK, summary="[docker0]"),
                        Result(state=state.OK, summary="(up)", details="Operational state: up"),
                        Result(state=state.OK, summary="MAC: AA:AA:AA:AA:AA:AA"),
                        Result(state=state.OK, summary="Speed: unknown"),
                    ],
                ),
                (
                    "4",
                    {"errors": {"both": ("abs", (10, 20))}, "speed": 0, "state": ["1"]},
                    [
                        Result(state=state.OK, summary="[wlp3s0]"),
                        Result(state=state.OK, summary="(up)", details="Operational state: up"),
                        Result(state=state.OK, summary="MAC: AA:AA:AA:AA:AA:BB"),
                        Result(state=state.OK, summary="Speed: unknown"),
                    ],
                ),
            ],
        ),
        (
            [
                ["[start_iplink]"],
                [
                    "1:",
                    "lo:",
                    "<LOOPBACK,UP,LOWER_UP>",
                    "mtu",
                    "65536",
                    "qdisc",
                    "noqueue",
                    "state",
                    "UNKNOWN",
                    "mode",
                    "DEFAULT",
                    "group",
                    "default",
                    "qlen",
                    "1000",
                ],
                ["link/loopback", "00:00:00:00:00:00", "brd", "00:00:00:00:00:00"],
                [
                    "2:",
                    "wlp3s0:",
                    "<BROADCAST,MULTICAST,UP,LOWER_UP>",
                    "mtu",
                    "1500",
                    "qdisc",
                    "fq_codel",
                    "state",
                    "UP",
                    "mode",
                    "DORMANT",
                    "group",
                    "default",
                    "qlen",
                    "1000",
                ],
                ["link/ether", "AA:AA:AA:AA:AA:AA", "brd", "BB:BB:BB:BB:BB:BB"],
                [
                    "3:",
                    "docker0:",
                    "<BROADCAST,MULTICAST,UP,LOWER_UP>",
                    "mtu",
                    "1500",
                    "qdisc",
                    "noqueue",
                    "state",
                    "UP",
                    "mode",
                    "DEFAULT",
                    "group",
                    "default",
                ],
                ["link/ether", "AA:AA:AA:AA:AA:AA", "brd", "BB:BB:BB:BB:BB:BB"],
                [
                    "5:",
                    "veth6a06585@if4:",
                    "<BROADCAST,MULTICAST,UP,LOWER_UP>",
                    "mtu",
                    "1500",
                    "qdisc",
                    "noqueue",
                    "master",
                    "docker0",
                    "state",
                    "UP",
                    "mode",
                    "DEFAULT",
                    "group",
                    "default",
                ],
                [
                    "link/ether",
                    "AA:AA:AA:AA:AA:AA",
                    "brd",
                    "BB:BB:BB:BB:BB:BB",
                    "link-netnsid",
                    "0",
                ],
                ["[end_iplink]"],
                [
                    "lo",
                    " 164379850  259656    0    0    0     0          0         0 164379850  259656    0    0    0     0       0          0",
                ],
                [
                    "wlp3s0",
                    " 130923553  201184    0    0    0     0          0     16078 23586281  142684    0    0    0     0       0          0",
                ],
                [
                    "docker0",
                    "       0       0    0    0    0     0          0         0    16250     184    0    0    0     0       0          0",
                ],
                [
                    "veth6a06585",
                    "       0       0    0    0    0     0          0         0    25963     287    0    0    0     0       0          0",
                ],
                ["[lo]"],
                ["Link detected", " yes"],
                ["Address", " 00", "00", "00", "00", "00", "00"],
                ["[docker0]"],
                ["Link detected", " yes"],
                ["Address", " AA", "AA", "AA", "AA", "AA", "AA"],
                ["[veth6a06585]"],
                ["Speed", " 10000Mb/s"],
                ["Duplex", " Full"],
                ["Auto-negotiation", " off"],
                ["Link detected", " yes"],
                ["Address", " AA", "AA", "AA", "AA", "AA", "AA"],
                ["[wlp3s0]"],
                ["Address", " AA", "AA", "AA", "AA", "AA", "AA"],
            ],
            [
                Service(
                    item="2", parameters={"discovered_oper_status": ["1"], "discovered_speed": 0}
                ),
                Service(
                    item="4", parameters={"discovered_oper_status": ["1"], "discovered_speed": 0}
                ),
            ],
            [
                (
                    "2",
                    {"errors": {"both": ("abs", (10, 20))}, "speed": 0, "state": ["1"]},
                    [
                        Result(state=state.OK, summary="[docker0]"),
                        Result(state=state.OK, summary="(up)", details="Operational state: up"),
                        Result(state=state.OK, summary="MAC: AA:AA:AA:AA:AA:AA"),
                        Result(state=state.OK, summary="Speed: unknown"),
                    ],
                ),
                (
                    "4",
                    {"errors": {"both": ("abs", (10, 20))}, "speed": 0, "state": ["1"]},
                    [
                        Result(state=state.OK, summary="[wlp3s0]"),
                        Result(state=state.OK, summary="(up)", details="Operational state: up"),
                        Result(state=state.OK, summary="MAC: AA:AA:AA:AA:AA:AA"),
                        Result(state=state.OK, summary="Speed: unknown"),
                    ],
                ),
            ],
        ),
        (
            [
                ["[start_iplink]"],
                [
                    "1:",
                    "lo:",
                    "<LOOPBACK,UP,LOWER_UP>",
                    "mtu",
                    "65536",
                    "qdisc",
                    "noqueue",
                    "state",
                    "UNKNOWN",
                    "mode",
                    "DEFAULT",
                    "group",
                    "default",
                    "qlen",
                    "1000",
                ],
                ["link/loopback", "00:00:00:00:00:00", "brd", "00:00:00:00:00:00"],
                [
                    "2:",
                    "wlp3s0:",
                    "<BROADCAST,MULTICAST,UP,LOWER_UP>",
                    "mtu",
                    "1500",
                    "qdisc",
                    "fq_codel",
                    "state",
                    "UNKNOWN",
                    "mode",
                    "DORMANT",
                    "group",
                    "default",
                    "qlen",
                    "1000",
                ],
                ["link/ether", "AA:AA:AA:AA:AA:AA", "brd", "BB:BB:BB:BB:BB:BB"],
                [
                    "3:",
                    "docker0:",
                    "<BROADCAST,MULTICAST,UP,LOWER_UP>",
                    "mtu",
                    "1500",
                    "qdisc",
                    "noqueue",
                    "state",
                    "UNKNOWN",
                    "mode",
                    "DEFAULT",
                    "group",
                    "default",
                ],
                ["link/ether", "AA:AA:AA:AA:AA:AA", "brd", "BB:BB:BB:BB:BB:BB"],
                [
                    "5:",
                    "veth6a06585@if4:",
                    "<BROADCAST,MULTICAST,UP,LOWER_UP>",
                    "mtu",
                    "1500",
                    "qdisc",
                    "noqueue",
                    "master",
                    "docker0",
                    "state",
                    "UNKNOWN",
                    "mode",
                    "DEFAULT",
                    "group",
                    "default",
                ],
                [
                    "link/ether",
                    "AA:AA:AA:AA:AA:AA",
                    "brd",
                    "BB:BB:BB:BB:BB:BB",
                    "link-netnsid",
                    "0",
                ],
                ["[end_iplink]"],
                [
                    "lo",
                    " 164379850  259656    0    0    0     0          0         0 164379850  259656    0    0    0     0       0          0",
                ],
                [
                    "wlp3s0",
                    " 130923553  201184    0    0    0     0          0     16078 23586281  142684    0    0    0     0       0          0",
                ],
                [
                    "docker0",
                    "       0       0    0    0    0     0          0         0    16250     184    0    0    0     0       0          0",
                ],
                [
                    "veth6a06585",
                    "       0       0    0    0    0     0          0         0    25963     287    0    0    0     0       0          0",
                ],
                ["[lo]"],
                ["Link detected", " yes"],
                ["Address", " 00", "00", "00", "00", "00", "00"],
                ["[docker0]"],
                ["Link detected", " yes"],
                ["Address", " AA", "AA", "AA", "AA", "AA", "AA"],
                ["[veth6a06585]"],
                ["Speed", " 10000Mb/s"],
                ["Duplex", " Full"],
                ["Auto-negotiation", " off"],
                ["Link detected", " yes"],
                ["Address", " AA", "AA", "AA", "AA", "AA", "AA"],
                ["[wlp3s0]"],
                ["Address", " AA", "AA", "AA", "AA", "AA", "AA"],
            ],
            [
                Service(
                    item="2", parameters={"discovered_oper_status": ["1"], "discovered_speed": 0}
                ),
                Service(
                    item="4", parameters={"discovered_oper_status": ["1"], "discovered_speed": 0}
                ),
            ],
            [
                (
                    "2",
                    {"errors": {"both": ("abs", (10, 20))}, "speed": 0, "state": ["1"]},
                    [
                        Result(state=state.OK, summary="[docker0]"),
                        Result(state=state.OK, summary="(up)", details="Operational state: up"),
                        Result(state=state.OK, summary="MAC: AA:AA:AA:AA:AA:AA"),
                        Result(state=state.OK, summary="Speed: unknown"),
                    ],
                ),
                (
                    "4",
                    {"errors": {"both": ("abs", (10, 20))}, "speed": 0, "state": ["1"]},
                    [
                        Result(state=state.OK, summary="[wlp3s0]"),
                        Result(state=state.OK, summary="(up)", details="Operational state: up"),
                        Result(state=state.OK, summary="MAC: AA:AA:AA:AA:AA:AA"),
                        Result(state=state.OK, summary="Speed: unknown"),
                    ],
                ),
            ],
        ),
        (
            [
                ["em0", "376716785370 417455222 0 0 0 0 0 0 383578105955 414581956 0 0 0 0 0 0"],
                ["tun0", "342545566242 0 259949262 0 0 0 0 0  0 19196 0 0  0 0"],
                ["tun1", "2422824602 0 2357563 0 0 0 0 0  0 0 0 0  0 0"],
                ["[em0]"],
                ["Speed", " 1000Mb/s"],
                ["Duplex", " Full"],
                ["Auto-negotiation", " on"],
                ["Link detected", " yes"],
                ["Address", " 00", "AA", "11", "BB", "22", "CC"],
                ["[tun0]"],
                ["Link detected", " yes"],
                ["Address", " 123"],
                ["[tun1]"],
                ["Link detected", " yes"],
                ["Address", " 456"],
            ],
            [
                Service(
                    item="1",
                    parameters={"discovered_oper_status": ["1"], "discovered_speed": 1000000000},
                ),
                Service(
                    item="2", parameters={"discovered_oper_status": ["1"], "discovered_speed": 0}
                ),
                Service(
                    item="3", parameters={"discovered_oper_status": ["1"], "discovered_speed": 0}
                ),
            ],
            [
                (
                    "1",
                    {"errors": {"both": ("abs", (10, 20))}, "speed": 1000000000, "state": ["1"]},
                    [
                        Result(state=state.OK, summary="[em0]"),
                        Result(state=state.OK, summary="(up)", details="Operational state: up"),
                        Result(state=state.OK, summary="MAC: 00:AA:11:BB:22:CC"),
                        Result(state=state.OK, summary="Speed: 1 GBit/s"),
                    ],
                ),
                (
                    "2",
                    {"errors": {"both": ("abs", (10, 20))}, "speed": 0, "state": ["1"]},
                    [
                        Result(state=state.OK, summary="[tun0]"),
                        Result(state=state.OK, summary="(up)", details="Operational state: up"),
                        Result(state=state.OK, summary="Speed: unknown"),
                    ],
                ),
                (
                    "3",
                    {"errors": {"both": ("abs", (10, 20))}, "speed": 0, "state": ["1"]},
                    [
                        Result(state=state.OK, summary="[tun1]"),
                        Result(state=state.OK, summary="(up)", details="Operational state: up"),
                        Result(state=state.OK, summary="Speed: unknown"),
                    ],
                ),
            ],
        ),
    ],
)
def test_lnx_if_regression(
    monkeypatch,
    string_table,
    discovery_results,
    items_params_results,
):
    section = lnx_if.parse_lnx_if(string_table)

    assert (
        list(
            lnx_if.discover_lnx_if(
                [interfaces.DISCOVERY_DEFAULT_PARAMETERS],
                section,
                None,
            )
        )
        == discovery_results
    )

    monkeypatch.setattr(interfaces, "get_value_store", lambda: {})
    for item, par, res in items_params_results:
        assert (
            list(
                lnx_if.check_lnx_if(
                    item,
                    par,
                    section,
                    None,
                )
            )
            == res
        )

    node_name = "node"
    for item, par, res in items_params_results:
        assert (
            list(
                lnx_if.cluster_check_lnx_if(
                    item,
                    par,
                    {node_name: section},
                    {},
                )
            )
            == [
                Result(  # type: ignore[call-overload]
                    state=res[0].state,
                    summary=res[0].summary + " on %s" % node_name if res[0].summary else None,
                    notice=res[0].summary + " on %s" % node_name if not res[0].summary else None,
                    details=res[0].details + " on %s" % node_name if res[0].details else None,
                ),
            ]
            + res[1:]
        )


def test_lnx_if_with_bonding(monkeypatch) -> None:

    section = lnx_if.parse_lnx_if(
        [
            ["[start_iplink]"],
            [
                "1:",
                "lo:",
                "<LOOPBACK,UP,LOWER_UP>",
                "mtu",
                "65536",
                "qdisc",
                "noqueue",
                "state",
                "UNKNOWN",
                "mode",
                "DEFAULT",
                "group",
                "default",
                "qlen",
                "1000",
            ],
            ["link/loopback", "00:00:00:00:00:00", "brd", "00:00:00:00:00:00"],
            [
                "2:",
                "wlp3s0:",
                "<BROADCAST,MULTICAST,UP,LOWER_UP>",
                "mtu",
                "1500",
                "qdisc",
                "fq_codel",
                "state",
                "UP",
                "mode",
                "DORMANT",
                "group",
                "default",
                "qlen",
                "1000",
            ],
            ["link/ether", "AA:AA:AA:AA:AA:BB", "brd", "BB:BB:BB:BB:BB:BB"],
            [
                "3:",
                "docker0:",
                "<BROADCAST,MULTICAST,UP,LOWER_UP>",
                "mtu",
                "1500",
                "qdisc",
                "noqueue",
                "state",
                "UP",
                "mode",
                "DEFAULT",
                "group",
                "default",
            ],
            ["link/ether", "AA:AA:AA:AA:AA:AA", "brd", "BB:BB:BB:BB:BB:BB"],
            [
                "5:",
                "veth6a06585@if4:",
                "<BROADCAST,MULTICAST,UP,LOWER_UP>",
                "mtu",
                "1500",
                "qdisc",
                "noqueue",
                "master",
                "docker0",
                "state",
                "UP",
                "mode",
                "DEFAULT",
                "group",
                "default",
            ],
            [
                "link/ether",
                "AA:AA:AA:AA:AA:AA",
                "brd",
                "BB:BB:BB:BB:BB:BB",
                "link-netnsid",
                "0",
            ],
            ["[end_iplink]"],
            [
                "lo",
                " 164379850  259656    0    0    0     0          0         0 164379850  259656    0    0    0     0       0          0",
            ],
            [
                "wlp3s0",
                " 130923553  201184    0    0    0     0          0     16078 23586281  142684    0    0    0     0       0          0",
            ],
            [
                "docker0",
                "       0       0    0    0    0     0          0         0    16250     184    0    0    0     0       0          0",
            ],
            [
                "veth6a06585",
                "       0       0    0    0    0     0          0         0    25963     287    0    0    0     0       0          0",
            ],
        ]
    )

    section_bonding: Mapping[str, bonding.Bond] = {
        "bond0": {
            "interfaces": {
                "wlp3s0": {
                    "hwaddr": "BB:BB:BB:BB:BB:BB",
                },
            },
        },
    }

    monkeypatch.setattr(interfaces, "get_value_store", lambda: {})
    assert list(
        lnx_if.check_lnx_if(
            "4",
            {"errors": {"both": ("abs", (10, 20))}, "speed": 0, "state": ["1"]},
            section,
            section_bonding,
        )
    ) == [
        Result(state=state.OK, summary="[wlp3s0]"),
        Result(state=state.OK, summary="(up)", details="Operational state: up"),
        Result(state=state.OK, summary="MAC: BB:BB:BB:BB:BB:BB"),
        Result(state=state.OK, summary="Speed: unknown"),
    ]


def test_inventory_lnx_if_empty() -> None:
    assert list(lnx_if.inventory_lnx_if(lnx_if.parse_lnx_if([]), None)) == [
        Attributes(
            path=["networking"],
            inventory_attributes={
                "available_ethernet_ports": 0,
                "total_ethernet_ports": 0,
                "total_interfaces": 0,
            },
            status_attributes={},
        ),
    ]


def test_inventory_lnx_if_no_bonding() -> None:
    assert [
        e
        for e in lnx_if.inventory_lnx_if(
            lnx_if.parse_lnx_if(
                [
                    ["[start_iplink]"],
                    [
                        "1:",
                        "wlp3s0:",
                        "<BROADCAST,MULTICAST>",
                        "mtu",
                        "1500",
                        "qdisc",
                        "fq_codel",
                        "state",
                        "UP",
                        "mode",
                        "DORMANT",
                        "group",
                        "default",
                        "qlen",
                        "1000",
                    ],
                    ["link/ether", "AA:AA:AA:AA:AA:AA", "brd", "BB:BB:BB:BB:BB:BB"],
                    ["[end_iplink]"],
                    ["wlp3s0", "130923553 201184 0 0 0 0 0 16078 23586281 142684 0 0 0 0 0 0"],
                ]
            ),
            None,
        )
        if isinstance(e, TableRow)
    ] == [
        TableRow(
            path=["networking", "interfaces"],
            key_columns={
                "index": 1,
                "description": "wlp3s0",
                "alias": "wlp3s0",
            },
            inventory_columns={
                "speed": 0,
                "phys_address": "AA:AA:AA:AA:AA:AA",
                "oper_status": 2,
                "port_type": 6,
                "available": True,
            },
            status_columns={},
        ),
    ]


def test_inventory_lnx_if_with_bonding() -> None:
    assert [
        e
        for e in lnx_if.inventory_lnx_if(
            lnx_if.parse_lnx_if(
                [
                    ["[start_iplink]"],
                    [
                        "1:",
                        "wlp3s0:",
                        "<BROADCAST,MULTICAST>",
                        "mtu",
                        "1500",
                        "qdisc",
                        "fq_codel",
                        "state",
                        "UP",
                        "mode",
                        "DORMANT",
                        "group",
                        "default",
                        "qlen",
                        "1000",
                    ],
                    ["link/ether", "AA:AA:AA:AA:AA:AA", "brd", "BB:BB:BB:BB:BB:BB"],
                    ["[end_iplink]"],
                    ["wlp3s0", "130923553 201184 0 0 0 0 0 16078 23586281 142684 0 0 0 0 0 0"],
                ]
            ),
            {
                "bond0": {
                    "interfaces": {
                        "wlp3s0": {
                            "hwaddr": "BB:BB:BB:BB:BB:BB",
                        },
                    },
                },
            },
        )
        if isinstance(e, TableRow)
    ] == [
        TableRow(
            path=["networking", "interfaces"],
            key_columns={
                "index": 1,
                "description": "wlp3s0",
                "alias": "wlp3s0",
            },
            inventory_columns={
                "speed": 0,
                "phys_address": "BB:BB:BB:BB:BB:BB",
                "oper_status": 2,
                "port_type": 6,
                "available": True,
                "bond": "bond0",
            },
            status_columns={},
        ),
    ]
