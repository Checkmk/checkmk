#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    get_average,
    get_rate,
    get_value_store,
    Metric,
    OIDEnd,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)

Section = Mapping[str, int]


def parse_pfsense_counter(string_table: StringTable) -> Section | None:
    names = {
        "1.0": "matched",
        "2.0": "badoffset",
        "3.0": "fragment",
        "4.0": "short",
        "5.0": "normalized",
        "6.0": "memdrop",
    }

    parsed = {}
    for end_oid, counter_text in string_table:
        parsed[names[end_oid]] = int(counter_text)
    return parsed or None


def discovery_pfsense_counter(section: Section) -> DiscoveryResult:
    yield Service()


def check_pfsense_counter(params: Mapping[str, Any], section: Section) -> CheckResult:
    namestoinfo = {
        "matched": "Packets that matched a rule",
        "badoffset": "Packets with bad offset",
        "fragment": "Fragmented packets",
        "short": "Short packets",
        "normalized": "Normalized packets",
        "memdrop": "Packets dropped due to memory limitations",
    }

    this_time = time.time()
    value_store = get_value_store()

    if backlog_minutes := params.get("average"):
        backlog_minutes = params["average"]
        yield Result(state=State.OK, summary="Values averaged over %d min" % params["average"])

    for what in section:
        levels = params.get(what)
        rate = get_rate(
            value_store, "pfsense_counter-%s" % what, this_time, section[what], raise_overflow=True
        )

        if backlog_minutes:
            yield Metric("fw_packets_" + what, rate, levels=levels)
            rate = get_average(
                value_store, "pfsense_counter-%srate" % what, this_time, rate, backlog_minutes
            )

        yield from check_levels_v1(
            rate,
            metric_name=f"fw{'_avg' if backlog_minutes else ''}_packets_{what}",
            levels_upper=levels,
            render_func=lambda x: "%.2f pkts" % x,
            label=namestoinfo[what],
        )


snmp_section_pfsense_counter = SimpleSNMPSection(
    name="pfsense_counter",
    detect=contains(".1.3.6.1.2.1.1.1.0", "pfsense"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12325.1.200.1",
        oids=[OIDEnd(), "2"],
    ),
    parse_function=parse_pfsense_counter,
)

check_plugin_pfsense_counter = CheckPlugin(
    name="pfsense_counter",
    service_name="pfSense Firewall Packet Rates",
    discovery_function=discovery_pfsense_counter,
    check_function=check_pfsense_counter,
    check_ruleset_name="pfsense_counter",
    check_default_parameters={
        "badoffset": (100.0, 10000.0),
        "short": (100.0, 10000.0),
        "memdrop": (100.0, 10000.0),
        "normalized": (100.0, 10000.0),
        "fragment": (100.0, 10000.0),
        "average": 3,
    },
)
