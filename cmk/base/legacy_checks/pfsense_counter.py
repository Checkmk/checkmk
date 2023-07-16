#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time
from typing import Any, Iterable, Mapping

from cmk.base.check_api import check_levels, get_average, get_rate, LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import contains, OIDEnd, SNMPTree
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable

Section = Mapping[str, int]

CheckResult = Iterable[tuple[int, str, list]]

DiscoveryResult = Iterable[tuple[None, dict]]


def parse_pfsense_counter(string_table: StringTable) -> Section:
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
    return parsed


def discovery_pfsense_counter(section: Section) -> DiscoveryResult:
    return [(None, {})]


def check_pfsense_counter(
    _no_item: None, params: Mapping[str, Any], section: Section
) -> CheckResult:
    namestoinfo = {
        "matched": "Packets that matched a rule",
        "badoffset": "Packets with bad offset",
        "fragment": "Fragmented packets",
        "short": "Short packets",
        "normalized": "Normalized packets",
        "memdrop": "Packets dropped due to memory limitations",
    }

    this_time = time.time()

    if backlog_minutes := params.get("average"):
        backlog_minutes = params["average"]
        yield 0, "Values averaged over %d min" % params["average"], []

    for what in section:
        levels = params.get(what)
        rate = get_rate("pfsense_counter-%s" % what, this_time, section[what])

        if backlog_minutes:
            yield 0, "", [("fw_packets_" + what, rate) + (levels or ())]
            rate = get_average("pfsense_counter-%srate" % what, this_time, rate, backlog_minutes)

        yield check_levels(
            rate,
            f"fw{'_avg' if backlog_minutes else ''}_packets_{what}",
            levels,
            human_readable_func=lambda x: "%.2f pkts",
            infoname=namestoinfo[what],
        )


check_info["pfsense_counter"] = LegacyCheckDefinition(
    detect=contains(".1.3.6.1.2.1.1.1.0", "pfsense"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12325.1.200.1",
        oids=[OIDEnd(), "2"],
    ),
    parse_function=parse_pfsense_counter,
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
