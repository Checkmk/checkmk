#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.hp_msa.agent_based.hp_msa_if import parse_hp_msa_if_pure
from cmk.plugins.lib import interfaces


def test_parse_hp_msa_if_pure() -> None:
    assert parse_hp_msa_if_pure(
        [
            ["port", "3", "durable-id", "hostport_A1"],
            ["port", "3", "port", "A1"],
            ["port", "3", "status", "Up"],
            ["port", "3", "actual-speed", "8Gb"],
            ["port", "5", "durable-id", "hostport_A2"],
            ["port", "5", "port", "A2"],
            ["port", "5", "status", "Disconnected"],
            ["port", "5", "actual-speed", "Auto"],
            ["host-port-statistics", "1", "durable-id", "hostport_A1"],
            ["host-port-statistics", "1", "data-read-numeric", "453669561808896"],
            ["host-port-statistics", "1", "data-written-numeric", "372010525295104"],
            ["host-port-statistics", "1", "queue-depth", "3"],
            ["host-port-statistics", "2", "durable-id", "hostport_A2"],
            ["host-port-statistics", "2", "data-read-numeric", "0"],
            ["host-port-statistics", "2", "data-written-numeric", "0"],
            ["host-port-statistics", "2", "queue-depth", "0"],
        ],
        1.0,
    ) == [
        interfaces.InterfaceWithCounters(
            interfaces.Attributes(
                index="1",
                descr="A1",
                alias="",
                type="6",
                speed=8000000000,
                oper_status="1",
                out_qlen=3,
            ),
            interfaces.Counters(in_octets=453669561808896, out_octets=372010525295104),
            timestamp=1.0,
        ),
        interfaces.InterfaceWithCounters(
            interfaces.Attributes(
                index="2",
                descr="A2",
                alias="",
                type="6",
                speed=0,
                oper_status="2",
                out_qlen=0,
            ),
            interfaces.Counters(in_octets=0, out_octets=0),
            timestamp=1.0,
        ),
    ]
