#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, State
from cmk.plugins.collection.agent_based.pfsense_counter import (
    check_pfsense_counter_pure,
    parse_pfsense_counter,
)


def test_parse_pfsense_counter() -> None:
    assert parse_pfsense_counter(
        [
            ["1.0", "42616538"],
            ["2.0", "0"],
            ["3.0", "1"],
            ["4.0", "34"],
            ["5.0", "65"],
            ["6.0", "0"],
        ]
    ) == {
        "matched": 42616538,
        "badoffset": 0,
        "fragment": 1,
        "short": 34,
        "normalized": 65,
        "memdrop": 0,
    }


def test_parse_pfsense_counter_empty() -> None:
    assert parse_pfsense_counter([]) is None


def test_check_pfsense_counter_pure() -> None:
    assert list(
        check_pfsense_counter_pure(
            {
                "average": 3,
                "badoffset": (100.0, 10000.0),
                "fragment": (0.0, 0.0),
                "short": (100.0, 10000.0),
                "normalized": (0.1, 10000.0),
                "memdrop": (100.0, 10000.0),
            },
            {
                "matched": 42616538,
                "badoffset": 0,
                "fragment": 1,
                "short": 34,
                "normalized": 65,
                "memdrop": 0,
            },
            100.0,
            {
                "pfsense_counter-matched": (0, 0.0),
                "pfsense_counter-badoffset": (0, 0.0),
                "pfsense_counter-fragment": (0, 0.0),
                "pfsense_counter-short": (0, 0.0),
                "pfsense_counter-normalized": (0, 0.0),
                "pfsense_counter-memdrop": (0, 0.0),
            },
        )
    ) == [
        Result(state=State.OK, summary="Values averaged over 3 min"),
        Metric("fw_packets_matched", 426165.38),
        Result(state=State.OK, summary="Packets that matched a rule: 426165.38 pkts"),
        Metric("fw_avg_packets_matched", 426165.38),
        Metric("fw_packets_badoffset", 0.0, levels=(100.0, 10000.0)),
        Result(state=State.OK, summary="Packets with bad offset: 0.00 pkts"),
        Metric("fw_avg_packets_badoffset", 0.0, levels=(100.0, 10000.0)),
        Metric("fw_packets_fragment", 0.01, levels=(0.0, 0.0)),
        Result(
            state=State.CRIT,
            summary="Fragmented packets: 0.01 pkts (warn/crit at 0.00 pkts/0.00 pkts)",
        ),
        Metric("fw_avg_packets_fragment", 0.01, levels=(0.0, 0.0)),
        Metric("fw_packets_short", 0.34, levels=(100.0, 10000.0)),
        Result(state=State.OK, summary="Short packets: 0.34 pkts"),
        Metric("fw_avg_packets_short", 0.34, levels=(100.0, 10000.0)),
        Metric("fw_packets_normalized", 0.65, levels=(0.1, 10000.0)),
        Result(
            state=State.WARN,
            summary="Normalized packets: 0.65 pkts (warn/crit at 0.10 pkts/10000.00 pkts)",
        ),
        Metric("fw_avg_packets_normalized", 0.65, levels=(0.1, 10000.0)),
        Metric("fw_packets_memdrop", 0.0, levels=(100.0, 10000.0)),
        Result(state=State.OK, summary="Packets dropped due to memory limitations: 0.00 pkts"),
        Metric("fw_avg_packets_memdrop", 0.0, levels=(100.0, 10000.0)),
    ]
