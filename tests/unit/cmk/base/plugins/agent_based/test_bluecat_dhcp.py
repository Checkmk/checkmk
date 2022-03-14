#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based import bluecat_dhcp
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result
from cmk.base.plugins.agent_based.agent_based_api.v1 import State as state


def check_bluecat_dhcp_ok():
    assert list(
        bluecat_dhcp.check_bluecat_dhcp(
            {
                "oper_states": {
                    "warning": [],
                    "critical": [],
                },
            },
            {
                "oper_state": 1,
                "leases": 11,
            },
        )
    ) == [
        Result(
            state=state.OK,
            summary="DHCP is running normally",
        ),
        Result(
            state=state.OK,
            summary="11 leases per second",
        ),
        Metric(
            "leases",
            11,
        ),
    ]


def check_bluecat_dhcp_crit():
    assert list(
        bluecat_dhcp.check_bluecat_dhcp(
            {
                "oper_states": {
                    "warning": [],
                    "critical": [5],
                },
            },
            {
                "oper_state": 5,
                "leases": 10,
            },
        )
    ) == [
        Result(
            state=state.CRIT,
            summary="DHCP is fault",
        ),
        Result(
            state=state.OK,
            summary="1 lease per second",
        ),
        Metric(
            "leases",
            1,
        ),
    ]


def check_bluecat_dhcp_one_lease():
    assert list(
        bluecat_dhcp.check_bluecat_dhcp(
            {
                "oper_states": {
                    "warning": [],
                    "critical": [],
                },
            },
            {
                "oper_state": 1,
                "leases": 1,
            },
        )
    ) == [
        Result(
            state=state.OK,
            summary="DHCP is running normally",
        ),
        Result(
            state=state.OK,
            summary="1 lease per second",
        ),
        Metric(
            "leases",
            1,
        ),
    ]


def test_cluster_check_bluecat_all_ok():
    assert list(
        bluecat_dhcp.cluster_check_bluecat_dhcp(
            {
                "oper_states": {
                    "warning": [],
                    "critical": [],
                },
            },
            {
                "node1": {
                    "oper_state": 1,
                    "leases": 11,
                },
                "node2": {
                    "oper_state": 1,
                    "leases": 11,
                },
            },
        )
    ) == [
        Result(
            state=state.OK,
            notice="[node1]: DHCP is running normally",
        ),
        Result(
            state=state.OK,
            notice="[node1]: 11 leases per second",
        ),
        Result(
            state=state.OK,
            notice="[node2]: DHCP is running normally",
        ),
        Result(
            state=state.OK,
            notice="[node2]: 11 leases per second",
        ),
        Result(
            state=state.OK,
            summary="DHCP is running normally on node2",
        ),
        Result(
            state=state.OK,
            summary="11 leases per second on node2",
        ),
        Metric(
            "leases",
            11,
        ),
    ]


def test_cluster_check_bluecat_one_ok():
    assert list(
        bluecat_dhcp.cluster_check_bluecat_dhcp(
            {
                "oper_states": {
                    "warning": [4],
                    "critical": [],
                },
            },
            {
                "node1": {
                    "oper_state": 1,
                    "leases": 13,
                },
                "node2": {
                    "oper_state": 4,
                    "leases": 11,
                },
            },
        )
    ) == [
        Result(
            state=state.OK,
            notice="[node1]: DHCP is running normally",
        ),
        Result(
            state=state.OK,
            notice="[node1]: 13 leases per second",
        ),
        Result(
            state=state.OK,
            notice="[node2]: DHCP is currently stopping(!)",
        ),
        Result(
            state=state.OK,
            notice="[node2]: 11 leases per second",
        ),
        Result(
            state=state.OK,
            summary="DHCP is running normally on node1",
        ),
        Result(
            state=state.OK,
            summary="13 leases per second on node1",
        ),
        Metric(
            "leases",
            13,
        ),
    ]


def test_cluster_check_bluecat_none_ok():
    assert list(
        bluecat_dhcp.cluster_check_bluecat_dhcp(
            {
                "oper_states": {
                    "warning": [1],
                    "critical": [2, 3],
                },
            },
            {
                "node1": {
                    "oper_state": 1,
                    "leases": 0,
                },
                "node2": {
                    "oper_state": 3,
                    "leases": 1,
                },
            },
        )
    ) == [
        Result(
            state=state.WARN,
            notice="[node1]: DHCP is running normally",
        ),
        Result(
            state=state.OK,
            notice="[node1]: 0 leases per second",
        ),
        Result(
            state=state.CRIT,
            notice="[node2]: DHCP is currently starting",
        ),
        Result(
            state=state.OK,
            notice="[node2]: 1 lease per second",
        ),
        Result(
            state=state.CRIT,
            summary="No node with OK DHCP state",
        ),
    ]
