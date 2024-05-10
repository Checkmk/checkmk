#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import Metric, Result, Service, State
from cmk.plugins.collection.agent_based.pfsense_if import (
    check_firewall_if_testable,
    DEFAULT_PARAMETERS,
    inventory_pfsense_if,
    parse_pfsense_if,
    Section,
)


def _section() -> Section:
    return parse_pfsense_if([["WAN", "9000"], ["LAN", "120"]])


def test_inventory_pfsense_if() -> None:
    assert list(inventory_pfsense_if(_section())) == [Service(item="WAN"), Service(item="LAN")]


def test_check_firewall_if_ok() -> None:
    value_store: dict[str, object] = {"ip4_in_blocked": (0, 0)}
    assert list(
        check_firewall_if_testable(
            "LAN",
            DEFAULT_PARAMETERS,
            _section(),
            value_store,
            60,
        )
    ) == [
        Result(state=State.OK, summary="Incoming IPv4 packets blocked: 2.00 pkts/s"),
        Metric("ip4_in_blocked", 2.0, levels=(100.0, 10000.0)),
    ]


def test_check_firewall_if_warn() -> None:
    value_store: dict[str, object] = {"ip4_in_blocked": (0, 0)}
    assert list(
        check_firewall_if_testable(
            "WAN",
            DEFAULT_PARAMETERS,
            _section(),
            value_store,
            60,
        )
    ) == [
        Result(
            state=State.WARN,
            summary="Incoming IPv4 packets blocked: 150.00 pkts/s (warn/crit at 100.00 pkts/s/10000.00 pkts/s)",
        ),
        Metric("ip4_in_blocked", 150.0, levels=(100.0, 10000.0)),
    ]
