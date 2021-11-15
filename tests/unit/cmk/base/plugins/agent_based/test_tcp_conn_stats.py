#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based import tcp_conn_stats
from cmk.base.plugins.agent_based.agent_based_api.v1 import Metric, Result, Service, State


def test_discovery_winperf_section():
    assert list(tcp_conn_stats.discover_tcp_connections({"ESTABLISHED": 3})) == [
        Service(),
    ]


def test_check_winperf_section():
    assert list(tcp_conn_stats.check_tcp_connections({}, {"ESTABLISHED": 3})) == [
        Result(
            state=State.OK,
            summary="Established: 3",
        ),
        Metric("ESTABLISHED", 3),
    ]


def test_check_tcp_conn_section():
    assert list(
        tcp_conn_stats.check_tcp_connections(
            {},
            {
                "ESTABLISHED": 29,
                "LISTEN": 26,
                # ...
            },
        )
    ) == [
        Result(
            state=State.OK,
            summary="Established: 29",
        ),
        Metric("ESTABLISHED", 29),
        Result(
            state=State.OK,
            notice="Listen: 26",
        ),
        Metric("LISTEN", 26),
    ]
