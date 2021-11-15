#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based import bluecat_dns
from cmk.base.plugins.agent_based.agent_based_api.v1 import Result
from cmk.base.plugins.agent_based.agent_based_api.v1 import State as state


def check_bluecat_dns_ok():
    assert list(
        bluecat_dns.check_bluecat_dns(
            {
                "oper_states": {
                    "warning": [],
                    "critical": [],
                },
            },
            {
                "oper_state": 1,
            },
        )
    ) == [
        Result(
            state=state.OK,
            summary="DNS is running normally",
        ),
    ]


def check_bluecat_dns_crit():
    assert list(
        bluecat_dns.check_bluecat_dns(
            {
                "oper_states": {
                    "warning": [],
                    "critical": [5],
                },
            },
            {
                "oper_state": 5,
            },
        )
    ) == [
        Result(
            state=state.CRIT,
            summary="DNS is fault",
        ),
    ]


def test_cluster_check_bluecat_all_ok():
    assert list(
        bluecat_dns.cluster_check_bluecat_dns(
            {
                "oper_states": {
                    "warning": [],
                    "critical": [],
                },
            },
            {
                "node1": {
                    "oper_state": 1,
                },
                "node2": {
                    "oper_state": 1,
                },
            },
        )
    ) == [
        Result(
            state=state.OK,
            notice="[node1]: DNS is running normally",
        ),
        Result(
            state=state.OK,
            notice="[node2]: DNS is running normally",
        ),
        Result(
            state=state.OK,
            summary="DNS is running normally on node2",
        ),
    ]


def test_cluster_check_bluecat_one_ok():
    assert list(
        bluecat_dns.cluster_check_bluecat_dns(
            {
                "oper_states": {
                    "warning": [4],
                    "critical": [],
                },
            },
            {
                "node1": {
                    "oper_state": 1,
                },
                "node2": {
                    "oper_state": 4,
                },
            },
        )
    ) == [
        Result(
            state=state.OK,
            notice="[node1]: DNS is running normally",
        ),
        Result(
            state=state.OK,
            notice="[node2]: DNS is currently stopping(!)",
        ),
        Result(
            state=state.OK,
            summary="DNS is running normally on node1",
        ),
    ]


def test_cluster_check_bluecat_none_ok():
    assert list(
        bluecat_dns.cluster_check_bluecat_dns(
            {
                "oper_states": {
                    "warning": [1],
                    "critical": [2, 3],
                },
            },
            {
                "node1": {
                    "oper_state": 1,
                },
                "node2": {
                    "oper_state": 3,
                },
            },
        )
    ) == [
        Result(
            state=state.WARN,
            summary="[node1]: DNS is running normally",
        ),
        Result(
            state=state.CRIT,
            summary="[node2]: DNS is currently starting",
        ),
        Result(
            state=state.CRIT,
            summary="No node with OK DNS state",
        ),
    ]
