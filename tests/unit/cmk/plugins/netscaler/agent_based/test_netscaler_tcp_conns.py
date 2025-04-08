#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.netscaler.agent_based.netscaler_tcp_conns import check, discover, parse, Section


def test_parse() -> None:
    assert Section(server_conns=39, client_conns=22) == parse([["39", "22"]])


def test_discover() -> None:
    assert [Service()] == list(discover(Section(server_conns=39, client_conns=22)))


def test_check() -> None:
    params = {"server_conns": (100, 200), "client_conns": (200, 300)}
    expected_result = [
        Result(state=State.OK, summary="Server connections: 39.00"),
        Metric("server_conns", 39.0, levels=(100.0, 200.0)),
        Result(state=State.OK, summary="Client connections: 22.00"),
        Metric("client_conns", 22.0, levels=(200.0, 300.0)),
    ]
    assert expected_result == list(check(params, Section(server_conns=39, client_conns=22)))
