#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Mapping

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_rate,
    get_value_store,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.mcafee.libgateway import DETECT_EMAIL_GATEWAY

Params = Mapping[str, tuple[float, float]]


def parse_mcafee_emailgateway_bridge(string_table: StringTable) -> StringTable | None:
    return string_table or None


def discover_mcafee_emailgateway_bridge(section: StringTable) -> DiscoveryResult:
    yield Service()


def check_mcafee_emailgateway_bridge(params: Params, section: StringTable) -> CheckResult:
    bridge_present, bridge_state, tcp_packets, udp_packets, icmp_packets = section[0]

    is_present = bridge_present == "0"
    yield Result(
        state=State.OK if is_present else State.CRIT,
        summary=f"Bridge: {'present' if is_present else 'not present'}",
    )
    is_up = bridge_state == "0"
    yield Result(
        state=State.OK if is_up else State.CRIT,
        summary=f"Status: {'UP' if is_up else 'down'}",
    )

    now = time.time()
    value_store = get_value_store()
    for title, packets in [
        ("TCP", tcp_packets),
        ("UDP", udp_packets),
        ("ICMP", icmp_packets),
    ]:
        key = title.lower()
        packets_rate = get_rate(
            value_store, f"mcafee_emailgateway_bridge.{key}", now, int(packets), raise_overflow=True
        )
        levels = params.get(key)
        yield from check_levels(
            packets_rate,
            levels_upper=("fixed", levels) if levels else None,
            metric_name=f"{key}_packets_received",
            render_func=lambda v: f"{v:.2f} packets received/s",
            label=title,
        )


snmp_section_mcafee_emailgateway_bridge = SimpleSNMPSection(
    name="mcafee_emailgateway_bridge",
    detect=DETECT_EMAIL_GATEWAY,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1230.2.4.1.2.2.1",
        oids=["1", "2", "3", "4", "5"],
    ),
    parse_function=parse_mcafee_emailgateway_bridge,
)


check_plugin_mcafee_emailgateway_bridge = CheckPlugin(
    name="mcafee_emailgateway_bridge",
    service_name="Bridge",
    discovery_function=discover_mcafee_emailgateway_bridge,
    check_function=check_mcafee_emailgateway_bridge,
    check_ruleset_name="mcafee_emailgateway_bridge",
    check_default_parameters={},
)
