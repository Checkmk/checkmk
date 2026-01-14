#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="arg-type"
# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="var-annotated"

import time

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import get_rate, get_value_store, render, SNMPTree
from cmk.plugins.f5_bigip.lib import F5_BIGIP

check_info = {}


def parse_f5_bigip_snat(string_table):
    snats = {}
    for line in string_table:
        name = line[0]
        snat_info = snats.setdefault(name, {})
        for index, stat in enumerate(
            (
                "if_in_pkts",
                "if_out_pkts",
                "if_in_octets",
                "if_out_octets",
                "connections_rate",
                "connections",
            ),
            start=1,
        ):
            try:
                stat_value = int(line[index])
            except ValueError:
                continue
            snat_info.setdefault(stat, []).append(stat_value)
    return {name: stats for name, stats in snats.items() if stats}


def discover_f5_bigip_snat(parsed):
    for name in parsed:
        yield name, {}


def check_f5_bigip_snat(item, params, parsed):
    if item in parsed:
        snat = parsed[item]

        summed_values = {}
        now = time.time()
        # Calculate counters
        for what in [
            "if_in_pkts",
            "if_out_pkts",
            "if_in_octets",
            "if_out_octets",
            "connections_rate",
        ]:
            summed_values.setdefault(what, 0)
            if what not in snat:
                continue
            for idx, entry in enumerate(snat[what]):
                rate = get_rate(get_value_store(), f"{what}.{idx}", now, entry, raise_overflow=True)
                summed_values[what] += rate

        # Calculate sum value
        for what, function in [("connections", sum)]:
            summed_values[what] = function(snat[what])

        # Current number of connections
        yield (
            0,
            "Client connections: %d" % summed_values["connections"],
            list(summed_values.items()),
        )

        # New connections per time
        yield 0, "Rate: %.2f/sec" % summed_values["connections_rate"]

        # Check configured limits
        map_paramvar_to_text = {
            "if_in_octets": "Incoming Bytes",
            "if_out_octets": "Outgoing Bytes",
            "if_total_octets": "Total Bytes",
            "if_in_pkts": "Incoming Packets",
            "if_out_pkts": "Outgoing Packets",
            "if_total_pkts": "Total Packets",
        }
        summed_values["if_total_octets"] = (
            summed_values["if_in_octets"] + summed_values["if_out_octets"]
        )
        summed_values["if_total_pkts"] = summed_values["if_in_pkts"] + summed_values["if_out_pkts"]
        for param_var, levels in params.items():
            if param_var.endswith("_lower") and isinstance(levels, tuple):
                levels = (None, None) + levels
            value = summed_values[param_var.rstrip("_lower")]
            state, infotext, _extra_perfdata = check_levels(
                value,
                param_var,
                levels,
                human_readable_func=render.disksize if "octets" in param_var else str,
                infoname=map_paramvar_to_text[param_var.rstrip("_lower")],
            )
            if state:
                yield state, infotext


check_info["f5_bigip_snat"] = LegacyCheckDefinition(
    name="f5_bigip_snat",
    detect=F5_BIGIP,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3375.2.2.9.2.3.1",
        oids=["1", "2", "3", "4", "5", "7", "8"],
    ),
    parse_function=parse_f5_bigip_snat,
    service_name="Source NAT %s",
    discovery_function=discover_f5_bigip_snat,
    check_function=check_f5_bigip_snat,
    check_ruleset_name="f5_bigip_snat",
)
