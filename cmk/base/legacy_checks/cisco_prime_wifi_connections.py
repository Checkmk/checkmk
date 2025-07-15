#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Cisco prime connection count check
This check will compare the sum of all 'count' entries against lower levels and additionally
output the sums of all individual connection types

see: https://d1nmyq4gcgsfi5.cloudfront.net/media/pi_3_3_devnet/api/v2/data/ClientCounts@_docs.html
"""

from collections.abc import Iterable, Mapping

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import StringTable
from cmk.base.check_legacy_includes.cisco_prime import parse_cisco_prime

check_info = {}

Section = Mapping


def parse_cisco_prime_wifi_connections(string_table: StringTable) -> Section:
    return parse_cisco_prime("clientCountsDTO", string_table)


def discover_cisco_prime_wifi_connections(section: Section) -> Iterable[tuple[None, dict]]:
    if section:
        yield None, {}


def check_cisco_prime_wifi_connections(item, params, parsed):
    """Sum up all individual counts for each connection type (as well as their sums
    indicated by 'count')"""
    keys = {
        "": "Total connections",
        "dot11a": "802.11a",
        "dot11b": "802.11b",
        "dot11g": "802.11g",
        "dot11ac": "802.11ac",
        "dot11n2_4": "802.11n24",
        "dot11n5": "802.11n5",
        "dot11ax2_4": "802.11ax24",
        "dot11ax5": "802.11ax5",
    }
    try:
        # Find the entry with all connection count values summed up ("key" = "All SSIDs")
        # and return only the it's value (a dict) with keys lowered for comparison
        sum_entry = next(
            {ctype.lower(): cname for ctype, cname in v.items()}
            for k, v in parsed.items()
            if v.get("key") == "All SSIDs"
        )
    except StopIteration:
        # Re-word the exception
        raise RuntimeError("No item with key='All SSIDs' found")

    for ctype, cname in keys.items():
        full_type_name = ctype + "authcount"
        # some newer standards might not be supported.
        try:
            count = sum_entry[full_type_name]
        except KeyError:
            continue
        lower_levels = params.get("levels_lower")
        if ctype == "":
            yield check_levels(
                count,
                "wifi_connection_total",
                (None, None) + (lower_levels or (None, None)),
                human_readable_func=int,
                infoname=cname,
            )
        else:
            yield 0, "%s: %d" % (cname, count), [("wifi_connection_" + ctype, count)]


check_info["cisco_prime_wifi_connections"] = LegacyCheckDefinition(
    name="cisco_prime_wifi_connections",
    parse_function=parse_cisco_prime_wifi_connections,
    service_name="Cisco Prime WiFi Connections",
    discovery_function=discover_cisco_prime_wifi_connections,
    check_function=check_cisco_prime_wifi_connections,
    check_ruleset_name="cisco_prime_wifi_connections",
    check_default_parameters={
        "levels_lower": None,
    },
)
