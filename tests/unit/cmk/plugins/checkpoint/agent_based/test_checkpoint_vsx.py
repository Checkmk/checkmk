#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import pytest

from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.base.legacy_checks.checkpoint_vsx import (
    check_checkpoint_vsx,
    check_checkpoint_vsx_connections,
    check_checkpoint_vsx_packets,
    check_checkpoint_vsx_status,
    check_checkpoint_vsx_traffic,
    discover_checkpoint_vsx,
    discover_vsx_connections,
    discover_vsx_packets,
    discover_vsx_traffic,
    parse_checkpoint_vsx,
    Section,
)

STRING_TABLE = [
    [
        [
            "0",
            "my_vsid1",
            "VSX Gateway",
            "192.168.1.11",
            "Standard",
            "ACTIVE",
            "Trust established",
            "Standby",
        ],
        [
            "1",
            "my_vsid2",
            "VSX Gateway",
            "192.168.1.111",
            "Standard",
            "STANDBY",
            "not known",
            "Standby",
        ],
    ],
    [
        ["104470", "499900", "150512", "369", "150143", "0", "46451524", "44344", "0", "2386"],
        ["104470", "499900", "150512", "369", "150143", "0", "46451524", "44344", "0", "2386"],
    ],
]

EXPECTED_SERVICES = [
    Service(item="my_vsid2 1"),
    Service(item="my_vsid1 0"),
]


def _section() -> Section:
    return parse_checkpoint_vsx(STRING_TABLE)


def test_discover_checkpoint_vsx() -> None:
    assert list(discover_checkpoint_vsx(_section())) == EXPECTED_SERVICES


def test_discover_checkpoint_traffic() -> None:
    assert list(discover_vsx_traffic(_section())) == EXPECTED_SERVICES


def test_discover_checkpoint_connections() -> None:
    assert list(discover_vsx_connections(_section())) == EXPECTED_SERVICES


def test_discover_checkpoint_packets() -> None:
    assert list(discover_vsx_packets(_section())) == EXPECTED_SERVICES


def test_check_checkpoint() -> None:
    assert list(check_checkpoint_vsx("my_vsid1 0", _section())) == [
        Result(state=State.OK, summary="Type: VSX Gateway"),
        Result(state=State.OK, summary="Main IP: 192.168.1.11"),
    ]


def test_check_checkpoint_connections() -> None:
    assert list(
        check_checkpoint_vsx_connections(
            "my_vsid1 0", {"levels_perc": ("fixed", (90.0, 95.0))}, _section()
        )
    ) == [
        Result(state=State.OK, summary="Used: 104470"),
        Metric("connections", 104470),
        Result(state=State.OK, summary="20.90%"),
    ]


def test_check_checkpoint_packets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "cmk.base.legacy_checks.checkpoint_vsx.get_value_store",
        lambda: {
            "packets_rate": (0, 150512),
            "packets_accepted_rate": (0, 150143),
            "packets_dropped_rate": (0, 369),
            "packets_rejected_rate": (0, 0),
            "packets_logged_rate": (0, 2386),
        },
    )

    assert list(
        check_checkpoint_vsx_packets(
            "my_vsid1 0",
            {
                "packets": ("no_levels", None),
                "packets_accepted": ("no_levels", None),
                "packets_dropped": ("no_levels", None),
                "packets_rejected": ("no_levels", None),
                "packets_logged": ("no_levels", None),
            },
            _section(),
        )
    ) == [
        Result(state=State.OK, summary="Total number of packets processed: 0.0/s"),
        Metric("packets", 0.0),
        Result(state=State.OK, summary="Total number of accepted packets: 0.0/s"),
        Metric("packets_accepted", 0.0),
        Result(
            state=State.OK,
            summary="Total number of dropped packets: 0.0/s",
        ),
        Metric("packets_dropped", 0.0),
        Result(state=State.OK, summary="Total number of rejected packets: 0.0/s"),
        Metric("packets_rejected", 0.0),
        Result(state=State.OK, summary="Total number of logs sent: 0.0/s"),
        Metric("packets_logged", 0.0),
    ]


def test_check_checkpoint_vsx_traffic(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "cmk.base.legacy_checks.checkpoint_vsx.get_value_store",
        lambda: {
            "bytes_accepted_rate": (0, 46451524),
            "bytes_dropped_rate": (0, 44344),
            "bytes_rejected_rate": (0, 0),
        },
    )
    assert list(
        check_checkpoint_vsx_traffic(
            "my_vsid1 0",
            {
                "bytes_accepted": ("no_levels", None),
                "bytes_dropped": ("no_levels", None),
                "bytes_rejected": ("no_levels", None),
            },
            _section(),
        )
    ) == [
        Result(state=State.OK, summary="Total number of bytes accepted: 0.00 B/s"),
        Metric("bytes_accepted", 0.0),
        Result(state=State.OK, summary="Total number of bytes dropped: 0.00 B/s"),
        Metric("bytes_dropped", 0.0),
        Result(state=State.OK, summary="Total number of bytes rejected: 0.00 B/s"),
        Metric("bytes_rejected", 0.0),
    ]


def test_check_checkpoint_vsx_status() -> None:
    assert list(check_checkpoint_vsx_status("my_vsid1 0", _section())) == [
        Result(state=State.OK, summary="HA Status: Standby"),
        Result(state=State.OK, summary="SIC Status: Trust established"),
        Result(state=State.OK, summary="Policy name: Standard"),
        Result(state=State.OK, summary="Policy type: ACTIVE"),
    ]


def test_check_checkpoint_vsx_status_crit() -> None:
    assert list(check_checkpoint_vsx_status("my_vsid2 1", _section())) == [
        Result(state=State.OK, summary="HA Status: Standby"),
        Result(state=State.CRIT, summary="SIC Status: not known"),
        Result(state=State.OK, summary="Policy name: Standard"),
        Result(state=State.CRIT, summary="Policy type: STANDBY (no policy installed)"),
    ]
