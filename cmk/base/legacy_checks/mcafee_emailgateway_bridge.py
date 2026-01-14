#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


import time

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import get_rate, get_value_store, SNMPTree, StringTable
from cmk.plugins.mcafee.libgateway import DETECT_EMAIL_GATEWAY

check_info = {}


def parse_mcafee_emailgateway_bridge(string_table: StringTable) -> StringTable | None:
    return string_table or None


def discover_mcafee_gateway_generic(info):
    return [(None, {})]


def check_mcafee_emailgateway_bridge(item, params, info):
    bridge_present, bridge_state, tcp_packets, udp_packets, icmp_packets = info[0]
    if bridge_present == "0":
        state = 0
        state_readable = "present"
    else:
        state = 2
        state_readable = "not present"
    yield state, "Bridge: %s" % state_readable

    if bridge_state == "0":
        state = 0
        state_readable = "UP"
    else:
        state = 2
        state_readable = "down"
    yield state, "Status: %s" % state_readable

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
        perfdata = ["%s_packets_received" % key, packets_rate]
        infotext = f"{title}: {packets_rate:.2f} packets received/s"
        state = 0
        if params.get(key):
            warn, crit = params[key]
            perfdata += [warn, crit]
            if packets_rate >= crit:
                state = 2
            elif packets_rate >= warn:
                state = 1
            if state:
                infotext += f" (warn/crit at {warn}/{crit} packets/s)"
        yield state, infotext, [tuple(perfdata)]


check_info["mcafee_emailgateway_bridge"] = LegacyCheckDefinition(
    name="mcafee_emailgateway_bridge",
    parse_function=parse_mcafee_emailgateway_bridge,
    detect=DETECT_EMAIL_GATEWAY,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1230.2.4.1.2.2.1",
        oids=["1", "2", "3", "4", "5"],
    ),
    service_name="Bridge",
    discovery_function=discover_mcafee_gateway_generic,
    check_function=check_mcafee_emailgateway_bridge,
    check_ruleset_name="mcafee_emailgateway_bridge",
)
