#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import MutableMapping

import pytest
import time_machine

from cmk.agent_based.v2 import GetRateError, Metric, Result, Service, State, StringTable
from cmk.plugins.f5_bigip.agent_based.f5_bigip_snat import (
    check_f5_bigip_snat,
    discover_f5_bigip_snat,
    parse_f5_bigip_snat,
    SnatParams,
)

from ..conftest import value_store

_NO_PARAMS: SnatParams = {}

# name, if_in_pkts, if_out_pkts, if_in_octets, if_out_octets, connections_rate, connections
_STRING_TABLE: StringTable = [
    ["SQL", "3", "120", "0", "0", "3", "0"],
    ["MI-VSP", "2559", "267523", "2216", "2134447", "167", "0"],
    ["RS6000", "31", "1296", "31", "1264", "25", "0"],
    ["LS_Test", "0", "0", "0", "0", "0", "0"],
    ["foobar", "2221", "2226331", "1509", "729471", "79", "0"],
    ["keycomp", "2534239", "2132789593", "2490959", "1972334953", "464", "2"],
    ["AS400_20", "304980", "103809944", "268938", "39785918", "22631", "10"],
    ["AS400_21", "0", "0", "0", "0", "0", "0"],
    ["keycomp2", "183", "32988", "168", "73366", "12", "0"],
    ["websrvc2", "0", "0", "0", "0", "0", "0"],
    ["AS2_proxy", "10", "712", "5", "236", "7", "0"],
    ["MI-SENTRY", "0", "0", "0", "0", "0", "0"],
    [
        "Outbound_SNAT",
        "160631017",
        "30383696271",
        "217420496",
        "220088423650",
        "8870002",
        "8279",
    ],
    ["foo.bar.com", "0", "0", "0", "0", "0", "0"],
    ["baz.buz.com", "45412", "57683523", "26828", "6379159", "462", "0"],
    ["wuz.huz-kuz.com", "0", "0", "0", "0", "0", "0"],
    ["bar.foo.com", "339", "13560", "7", "280", "339", "0"],
    ["foo.bar.buz-huz.com", "0", "0", "0", "0", "0", "0"],
]

_SECTION = parse_f5_bigip_snat(_STRING_TABLE)

# The same counter values one minute earlier, so every rate is zero.
_UNCHANGED: MutableMapping[str, object] = {
    "if_in_pkts.0": (0.0, 10),
    "if_out_pkts.0": (0.0, 712),
    "if_in_octets.0": (0.0, 5),
    "if_out_octets.0": (0.0, 236),
    "connections_rate.0": (0.0, 7),
}

# One minute earlier, so Outbound_SNAT yields 10/s and 20/s packets, 100 B/s and 200 B/s.
_OUTBOUND_A_MINUTE_AGO: MutableMapping[str, object] = {
    "if_in_pkts.0": (0.0, 160631017 - 60 * 10),
    "if_out_pkts.0": (0.0, 30383696271 - 60 * 20),
    "if_in_octets.0": (0.0, 217420496 - 60 * 100),
    "if_out_octets.0": (0.0, 220088423650 - 60 * 200),
    "connections_rate.0": (0.0, 8870002 - 60),
}


def test_parse_f5_bigip_snat() -> None:
    assert _SECTION["keycomp"] == {
        "if_in_pkts": [2534239],
        "if_out_pkts": [2132789593],
        "if_in_octets": [2490959],
        "if_out_octets": [1972334953],
        "connections_rate": [464],
        "connections": [2],
    }


def test_parse_f5_bigip_snat_skips_counters_the_device_does_not_answer() -> None:
    """Empty columns mean the device does not expose those OIDs."""
    parsed = parse_f5_bigip_snat([["sparse", "", "", "1024", "", "0", "1"]])
    assert parsed["sparse"] == {"if_in_octets": [1024], "connections_rate": [0], "connections": [1]}


def test_parse_f5_bigip_snat_rejects_a_non_numeric_counter() -> None:
    """A value that is present has to be a counter; anything else is a broken MIB."""
    with pytest.raises(ValueError):
        parse_f5_bigip_snat([["broken", "abc", "0", "0", "0", "0", "0"]])


def test_parse_f5_bigip_snat_empty_input() -> None:
    assert parse_f5_bigip_snat([]) == {}


def test_discover_f5_bigip_snat() -> None:
    """Every SNAT is discovered, including the ones reporting only zeroes."""
    assert list(discover_f5_bigip_snat(_SECTION)) == [
        Service(item="SQL"),
        Service(item="MI-VSP"),
        Service(item="RS6000"),
        Service(item="LS_Test"),
        Service(item="foobar"),
        Service(item="keycomp"),
        Service(item="AS400_20"),
        Service(item="AS400_21"),
        Service(item="keycomp2"),
        Service(item="websrvc2"),
        Service(item="AS2_proxy"),
        Service(item="MI-SENTRY"),
        Service(item="Outbound_SNAT"),
        Service(item="foo.bar.com"),
        Service(item="baz.buz.com"),
        Service(item="wuz.huz-kuz.com"),
        Service(item="bar.foo.com"),
        Service(item="foo.bar.buz-huz.com"),
    ]


@time_machine.travel(60.0)
def test_check_f5_bigip_snat_no_levels() -> None:
    """Counters that did not move report every metric at zero."""
    with value_store(_UNCHANGED):
        assert list(check_f5_bigip_snat("AS2_proxy", _NO_PARAMS, _SECTION)) == [
            Result(state=State.OK, summary="Client connections: 0"),
            Metric("if_in_pkts", 0.0),
            Metric("if_out_pkts", 0.0),
            Metric("if_in_octets", 0.0),
            Metric("if_out_octets", 0.0),
            Metric("connections_rate", 0.0),
            Metric("connections", 0.0),
            Result(state=State.OK, summary="Rate: 0.00/sec"),
        ]


@time_machine.travel(60.0)
def test_check_f5_bigip_snat_sixty_four_bit_counters() -> None:
    """Outbound_SNAT counts past 2**32, so the rates have to be computed on 64 bits."""
    with value_store(_OUTBOUND_A_MINUTE_AGO):
        results = list(check_f5_bigip_snat("Outbound_SNAT", _NO_PARAMS, _SECTION))
    assert results == [
        Result(state=State.OK, summary="Client connections: 8279"),
        Metric("if_in_pkts", 10.0),
        Metric("if_out_pkts", 20.0),
        Metric("if_in_octets", 100.0),
        Metric("if_out_octets", 200.0),
        Metric("connections_rate", 1.0),
        Metric("connections", 8279.0),
        Result(state=State.OK, summary="Rate: 1.00/sec"),
    ]


@time_machine.travel(60.0)
def test_check_f5_bigip_snat_traffic_levels() -> None:
    """Configured levels are reported as notices, bytes rendered as sizes."""
    params: SnatParams = {
        "if_in_octets": ("fixed", (50.0, 150.0)),
        "if_total_octets": ("fixed", (250.0, 400.0)),
        "if_out_pkts_lower": ("fixed", (30.0, 25.0)),
    }
    with value_store(_OUTBOUND_A_MINUTE_AGO):
        results = list(check_f5_bigip_snat("Outbound_SNAT", params, _SECTION))
    assert results[8:] == [
        Result(state=State.WARN, notice="Incoming Bytes: 100 B (warn/crit at 50 B/150 B)"),
        Result(state=State.WARN, notice="Total Bytes: 300 B (warn/crit at 250 B/400 B)"),
        Result(state=State.CRIT, notice="Outgoing Packets: 20.0 (warn/crit below 30.0/25.0)"),
    ]


@time_machine.travel(60.0)
def test_check_f5_bigip_snat_unknown_item() -> None:
    with value_store(_UNCHANGED):
        assert list(check_f5_bigip_snat("nonexistent", _NO_PARAMS, _SECTION)) == []


@time_machine.travel(60.0)
def test_check_f5_bigip_snat_counter_reset() -> None:
    """A counter that went backwards raises, so the engine keeps the previous state."""
    with value_store(_UNCHANGED), pytest.raises(GetRateError):
        list(check_f5_bigip_snat("LS_Test", _NO_PARAMS, _SECTION))
