#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

"""Cisco prime connection count check
This check will compare the sum of all 'count' entries against lower levels and additionally
output the sums of all individual connection types

see: https://d1nmyq4gcgsfi5.cloudfront.net/media/pi_3_3_devnet/api/v2/data/ClientCounts@_docs.html
"""

import json
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.legacy.conversion import (
    # Temporary compatibility layer until we migrate the corresponding ruleset.
    check_levels_legacy_compatible as check_levels,
)
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    State,
    StringTable,
)

Section = Mapping[str, Mapping[str, object]]


def parse_cisco_prime_wifi_connections(string_table: StringTable) -> Section:
    """Parse JSON and return queryResponse/entity entries keyed by "@id".

    See https://solutionpartner.cisco.com/media/prime-infrastructure-api-reference-v3-0/192.168.115.187/webacs/api/v1/data/ClientCountscc3b.html
    """
    elements = json.loads(string_table[0][0])["queryResponse"]["entity"]
    return {elem["clientCountsDTO"]["@id"]: elem["clientCountsDTO"] for elem in elements}


def discover_cisco_prime_wifi_connections(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


def check_cisco_prime_wifi_connections(params: Mapping[str, Any], section: Section) -> CheckResult:
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
            for k, v in section.items()
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
        assert isinstance(count, int | float)
        lower_levels = params.get("levels_lower")
        if ctype == "":
            yield from check_levels(
                count,
                "wifi_connection_total",
                (None, None) + (lower_levels or (None, None)),
                human_readable_func=int,
                infoname=cname,
            )
        else:
            yield Result(state=State.OK, summary=f"{cname}: {int(count)}")
            yield Metric(f"wifi_connection_{ctype}", count)


agent_section_cisco_prime_wifi_connections = AgentSection(
    name="cisco_prime_wifi_connections",
    parse_function=parse_cisco_prime_wifi_connections,
)


check_plugin_cisco_prime_wifi_connections = CheckPlugin(
    name="cisco_prime_wifi_connections",
    service_name="Cisco Prime WiFi Connections",
    discovery_function=discover_cisco_prime_wifi_connections,
    check_function=check_cisco_prime_wifi_connections,
    check_ruleset_name="cisco_prime_wifi_connections",
    check_default_parameters={
        "levels_lower": None,
    },
)
