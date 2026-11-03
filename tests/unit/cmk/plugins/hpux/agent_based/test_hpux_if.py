#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.plugins.hpux.agent_based.hpux_if import parse_hpux_if_pure
from cmk.plugins.lib import interfaces


def test_parse_hpux_if_pure() -> None:
    assert parse_hpux_if_pure(
        [
            ["***", "lan2", "64", "bit", "MIB", "statistics:"],
            ["Interface", "Name", "=", "lan2"],
            ["PPA", "Number", "=", "2"],
            ["Description", "=", "lan2", "HP", "PCI-X", "1000Mbps", "Release", "B.11.31.1103"],
            ["Interface", "Type", "=", "1000Base-SX"],
            ["MTU", "Size", "=", "1500"],
            ["Speed", "=", "1", "Gbps"],
            ["Station", "Address", "=", "0x001A4BAC31B2"],
            ["Administration", "Status", "=", "UP"],
            ["Operation", "Status", "=", "UP"],
            ["Inbound", "Octets", "=", "46729081959"],
            ["Inbound", "Unicast", "Packets", "=", "0"],
            ["Inbound", "Broadcast", "Packets", "=", "452745382"],
            ["Inbound", "Discards", "=", "117536051"],
            ["Inbound", "Errors", "=", "0"],
            ["Inbound", "Unknown", "Protocols", "=", "337286760"],
            ["Outbound", "Octets", "=", "4711"],
            ["Outbound", "Errors", "=", "3"],
            ["Interface", "Alias", "="],
            ["***", "lan3", "64", "bit", "MIB", "statistics:"],
            ["Interface", "Name", "=", "lan3"],
            ["PPA", "Number", "=", "3"],
            ["Speed", "=", "100", "Mbps"],
            ["Operation", "Status", "=", "DOWN"],
        ],
        1.0,
    ) == [
        interfaces.InterfaceWithCounters(
            interfaces.Attributes(
                index="2",
                descr="lan2",
                alias="lan2",
                type="6",
                speed=1000000000.0,
                oper_status="1",
                phys_address="\x00\x1aK\xac1\xb2",
            ),
            interfaces.Counters(
                in_octets=46729081959,
                in_ucast=0,
                in_bcast=452745382,
                in_disc=117536051,
                in_err=0,
                out_octets=4711,
                out_err=3,
            ),
            timestamp=1.0,
        ),
        interfaces.InterfaceWithCounters(
            interfaces.Attributes(
                index="3",
                descr="lan3",
                alias="lan3",
                type="6",
                speed=100000000.0,
                oper_status="2",
            ),
            interfaces.Counters(),
            timestamp=1.0,
        ),
    ]
