#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import MutableMapping

import pytest
import time_machine

from cmk.agent_based.v2 import Metric, Result, Service, State, StringTable
from cmk.plugins.f5_bigip.agent_based.f5_bigip_vserver import (
    check_f5_bigip_vserver,
    discover_f5_bigip_vserver,
    get_ip_address_human_readable,
    parse_f5_bigip_vserver,
    VServer,
    VServerParams,
)

from ..conftest import value_store

_CHILDREN_DOWN_DETAIL = "The children pool member(s) are down"

# name, status, enabled, detail, packed ip, then the counters of _COUNTERS
_STRING_TABLE: StringTable = [
    [
        "/Common/sight-seeing.wurmhole.univ",
        "1",
        "1",
        "The virtual server is available",
        "\xd4;xK",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "0",
        "",
    ],
    [
        "/Common/www.wurmhole.univ_HTTP2HTTPS",
        "4",
        "1",
        "The children pool member(s) either don't have service checking enabled",
        "\xd4;xI",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "42",
        "0",
        "",
    ],
    [
        "/Common/starfleet.space",
        "4",
        "",
        "To infinity and beyond!",
        "\xde\xca\xff\xed",
        "",
        "",
        "",
        "",
        "42",
        "32",
        "",
        "",
        "0",
        "",
    ],
    [
        # Every counter populated; the durations are reported in milliseconds.
        "VS_BM",
        "1",
        "1",
        "The virtual server is available",
        "\xac\x14\xcad",
        "38",
        "76766",
        "10744",
        "70981",
        "84431",
        "10961763",
        "83403367",
        "2535",
        "0",
        "0",
    ],
    [
        "VS_DISABLED",
        "0",
        "0",
        "Disabled by the administrator",
        "\xac\x14\xcad",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "0",
        "",
    ],
    [
        "/Common/down.wurmhole.univ",
        "3",
        "1",
        _CHILDREN_DOWN_DETAIL,
        "\xd4;xK",
        "1",
        "2",
        "3",
        "400",
        "500",
        "6000",
        "7000",
        "80",
        "9",
        "10",
    ],
]

_NO_PARAMS = VServerParams()


@pytest.mark.parametrize(
    "packed, expected",
    [
        pytest.param("\xd4;xK", "212.59.120.75", id="ipv4"),
        pytest.param("\xde\xca\xff\xed", "222.202.255.237", id="ipv4 high bytes"),
        pytest.param("1.2.3.4", "-", id="not a packed address"),
        pytest.param("\n\x10˂", "-", id="codepoint above one byte"),
        pytest.param("", "-", id="empty"),
    ],
)
def test_get_ip_address_human_readable(packed: str, expected: str) -> None:
    assert get_ip_address_human_readable(packed) == expected


def test_parse_f5_bigip_vserver() -> None:
    section = parse_f5_bigip_vserver(_STRING_TABLE)
    assert section["/Common/starfleet.space"] == VServer(
        status="4",
        enabled="",
        detail="To infinity and beyond!",
        ip_address="222.202.255.237",
        counters={"if_out_pkts": [42.0], "if_in_octets": [32.0], "connections": [0.0]},
    )


def test_parse_f5_bigip_vserver_scales_durations() -> None:
    """The connection durations are reported in milliseconds."""
    counters = parse_f5_bigip_vserver(_STRING_TABLE)["/Common/down.wurmhole.univ"].counters
    assert counters["connections_duration_min"] == [0.001]
    assert counters["connections_duration_max"] == [0.002]
    assert counters["connections_duration_mean"] == [0.003]


def test_discover_f5_bigip_vserver() -> None:
    assert list(discover_f5_bigip_vserver(parse_f5_bigip_vserver(_STRING_TABLE))) == [
        Service(item="/Common/sight-seeing.wurmhole.univ"),
        Service(item="/Common/www.wurmhole.univ_HTTP2HTTPS"),
        Service(item="/Common/starfleet.space"),
        Service(item="VS_BM"),
        Service(item="VS_DISABLED"),
        Service(item="/Common/down.wurmhole.univ"),
    ]


@time_machine.travel(60.0)
def test_check_f5_bigip_vserver_available() -> None:
    with value_store():
        assert list(
            check_f5_bigip_vserver(
                "/Common/sight-seeing.wurmhole.univ",
                _NO_PARAMS,
                parse_f5_bigip_vserver(_STRING_TABLE),
            )
        ) == [
            Result(state=State.OK, summary="Virtual Server with IP 212.59.120.75 is enabled"),
            Result(
                state=State.OK,
                summary="State is up and available, Detail: The virtual server is available",
            ),
            Result(state=State.OK, summary="Client connections: 0"),
            Metric("connections", 0.0),
        ]


@time_machine.travel(60.0)
def test_check_f5_bigip_vserver_unknown_enabled_state() -> None:
    """An enabled state the device does not document is reported as WARN."""
    with value_store():
        results = list(
            check_f5_bigip_vserver(
                "/Common/starfleet.space", _NO_PARAMS, parse_f5_bigip_vserver(_STRING_TABLE)
            )
        )
    assert results[0] == Result(
        state=State.WARN, summary="Virtual Server with IP 222.202.255.237 is in unknown state"
    )
    assert results[1] == Result(
        state=State.WARN, summary="State availability is unknown, Detail: To infinity and beyond!"
    )


@time_machine.travel(60.0)
def test_check_f5_bigip_vserver_state_mapping() -> None:
    """The state map overrides the state derived from the device status."""
    params = VServerParams(state={"availability_is_unknown": State.CRIT.value})
    with value_store():
        results = list(
            check_f5_bigip_vserver(
                "/Common/starfleet.space", params, parse_f5_bigip_vserver(_STRING_TABLE)
            )
        )
    assert results[1] == Result(
        state=State.CRIT, summary="State availability is unknown, Detail: To infinity and beyond!"
    )


@pytest.mark.parametrize(
    "params, expected_state",
    [
        pytest.param(VServerParams(), State.OK, id="defaults to OK"),
        pytest.param(
            VServerParams(state={"children_pool_members_down_if_not_available": State.WARN.value}),
            State.WARN,
            id="overridden by the state map",
        ),
    ],
)
@time_machine.travel(60.0)
def test_check_f5_bigip_vserver_children_pool_members_down(
    params: VServerParams, expected_state: State
) -> None:
    """A server that is unavailable only because its pool members are down."""
    with value_store():
        results = list(
            check_f5_bigip_vserver(
                "/Common/down.wurmhole.univ", params, parse_f5_bigip_vserver(_STRING_TABLE)
            )
        )
    assert results[1] == Result(
        state=expected_state,
        summary=f"State is not available, Detail: {_CHILDREN_DOWN_DETAIL}",
    )


@time_machine.travel(60.0)
def test_check_f5_bigip_vserver_traffic_levels() -> None:
    # One minute earlier, so the counters yield 5/s and 6/s packets, 70/s and 80/s bytes.
    seeded_store: MutableMapping[str, object] = {
        "if_in_pkts.0": (0.0, 100),
        "if_out_pkts.0": (0.0, 140),
        "if_in_octets.0": (0.0, 1800),
        "if_out_octets.0": (0.0, 2200),
        "connections_rate.0": (0.0, 20),
        "packet_velocity_asic.0": (0.0, 4),
    }
    params = VServerParams(
        connections=("fixed", (5.0, 10.0)),
        if_total_octets=("fixed", (100.0, 200.0)),
        if_in_pkts_lower=("fixed", (10.0, 8.0)),
    )
    with value_store(seeded_store):
        results = list(
            check_f5_bigip_vserver(
                "/Common/down.wurmhole.univ", params, parse_f5_bigip_vserver(_STRING_TABLE)
            )
        )
    assert results[2] == Result(
        state=State.WARN, summary="Client connections: 9 (warn/crit at 5/10)"
    )
    # The traffic levels are checked octets first, then packets.
    assert results[-3:] == [
        Result(state=State.OK, summary="Connections rate: 1.00/sec"),
        Result(state=State.WARN, notice="Total bytes: 150 B/s (warn/crit at 100 B/s/200 B/s)"),
        Result(state=State.CRIT, notice="Incoming packets: 5.0/s (warn/crit below 10.0/s/8.0/s)"),
    ]


@time_machine.travel(60.0)
def test_check_f5_bigip_vserver_unknown_item() -> None:
    with value_store():
        assert (
            list(
                check_f5_bigip_vserver(
                    "nonexistent", _NO_PARAMS, parse_f5_bigip_vserver(_STRING_TABLE)
                )
            )
            == []
        )


@time_machine.travel(60.0)
def test_check_f5_bigip_vserver_reports_every_aggregated_metric() -> None:
    """A vserver with all counters populated reports the full set, sorted by name."""
    unchanged: MutableMapping[str, object] = {
        "if_in_pkts.0": (0.0, 70981),
        "if_out_pkts.0": (0.0, 84431),
        "if_in_octets.0": (0.0, 10961763),
        "if_out_octets.0": (0.0, 83403367),
        "connections_rate.0": (0.0, 2535),
        "packet_velocity_asic.0": (0.0, 0),
    }
    with value_store(unchanged):
        results = list(
            check_f5_bigip_vserver("VS_BM", _NO_PARAMS, parse_f5_bigip_vserver(_STRING_TABLE))
        )

    assert results[0] == Result(
        state=State.OK, summary="Virtual Server with IP 172.20.202.100 is enabled"
    )
    assert results[1] == Result(
        state=State.OK,
        summary="State is up and available, Detail: The virtual server is available",
    )
    assert results[2] == Result(state=State.OK, summary="Client connections: 0")
    assert results[3:15] == [
        Metric("connections", 0.0),
        Metric("connections_duration_max", 76.766),
        Metric("connections_duration_mean", 10.744),
        Metric("connections_duration_min", 0.038),
        Metric("connections_rate", 0.0),
        Metric("if_in_octets", 0.0),
        Metric("if_in_pkts", 0.0),
        Metric("if_out_octets", 0.0),
        Metric("if_out_pkts", 0.0),
        Metric("if_total_octets", 0.0),
        Metric("if_total_pkts", 0.0),
        Metric("packet_velocity_asic", 0.0),
    ]
    assert results[15] == Result(state=State.OK, summary="Connections rate: 0.00/sec")


@time_machine.travel(60.0)
def test_check_f5_bigip_vserver_disabled() -> None:
    """An administratively disabled vserver: enabled state NONE, status disabled."""
    with value_store():
        results = list(
            check_f5_bigip_vserver("VS_DISABLED", _NO_PARAMS, parse_f5_bigip_vserver(_STRING_TABLE))
        )
    assert results[:2] == [
        Result(state=State.OK, summary="Virtual Server with IP 172.20.202.100 is NONE"),
        Result(
            state=State.WARN,
            summary="State is disabled, Detail: Disabled by the administrator",
        ),
    ]
