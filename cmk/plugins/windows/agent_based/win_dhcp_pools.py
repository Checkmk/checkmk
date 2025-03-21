#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Mapping, Sequence
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_rate,
    get_value_store,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.lib.dhcp_pools import check_dhcp_pools_levels

# Example outputs from agent:
#
# <<<win_dhcp_pools>>>
#
# MIB-Anzahl:
#     Entdeckungen = 0.
#     Angebote = 0.
#     Anforderungen = 0.
#     Acks = 0.
#     Naks = 0.
#     Abweisungen = 0.
#     Freigaben = 0.
#     ServerStartTime = Dienstag, 29. Juni 2010 19:08:55
#     Bereiche = 1.
#     Subnetz = 192.168.123.0.
#         Anzahl der verwendeten Adressen = 0.
#         Anzahl der freien Adressen = 239.
#         Anzahl der anstehenden Angebote = 0.
#
# MIBCounts:
#         Discovers = 0.
#         Offers = 0.
#         Requests = 0.
#         Acks = 1.
#         Naks = 0.
#         Declines = 0.
#         Releases = 0.
#         ServerStartTime = Sunday, May 25, 2008 12:38:06 PM
#         Scopes = 1.
#         Subnet = 172.16.11.0.
#                 No. of Addresses in use = 1.
#                 No. of free Addresses = 23.
#                 No. of pending offers = 0.


Section = Sequence[tuple[str, ...]]


#   .--Pools---------------------------------------------------------------.
#   |                       ____             _                             |
#   |                      |  _ \ ___   ___ | |___                         |
#   |                      | |_) / _ \ / _ \| / __|                        |
#   |                      |  __/ (_) | (_) | \__ \                        |
#   |                      |_|   \___/ \___/|_|___/                        |
#   |                                                                      |
#   '----------------------------------------------------------------------'

# Attention:
#
# Tried to get the win-agent plug-in to report always in utf-8, unfortunately without luck.
# ...that's the reason why french translations with special characters must get provided like here.

_WIN_DHCP_POOLS_STATS_TRANSLATE = {
    "Entdeckungen": "Discovers",
    "Angebote": "Offers",
    "Anforderungen": "Requests",
    "Acks": "Acks",
    "Naks": "Nacks",
    "Abweisungen": "Declines",
    "Freigaben": "Releases",
    "Subnetz": "Subnet",
    "Bereiche": "Scopes",
    "Anzahl der verwendeten Adressen": "No. of Addresses in use",
    "Anzahl der freien Adressen": "No. of free Addresses",
    "Anzahl der anstehenden Angebote": "No. of pending offers",
    "D\x82couvertes": "Discovers",
    "Offres": "Offers",
    "Requ\x88tes": "Requests",
    "AR": "Acks",
    "AR n\x82g.": "Nacks",
    "Refus": "Declines",
    "Lib\x82rations": "Releases",
    "Sous-r\x82seau": "Subnet",
    "\x90tendues": "Scopes",
    "Nb d'adresses utilis\x82es": "No. of Addresses in use",
    "Nb d'adresses libres": "No. of free Addresses",
    "Nb d'offres en attente": "No. of pending offers",
}


def parse_win_dhcp_pools(string_table: StringTable) -> Section:
    return [tuple(" ".join(line).rstrip(".").split(" = ")) for line in string_table]


agent_section_win_dhcp_pools = AgentSection(
    name="win_dhcp_pools",
    parse_function=parse_win_dhcp_pools,
)


def _safe_int(raw: str) -> int:
    """
    Taken from the legacy API to allow migration.
    We really should parse properly :-(
    """
    try:
        return int(raw)
    except ValueError:
        return 0


def discover_win_dhcp_pools(params: Mapping[str, Any], section: Section) -> DiscoveryResult:
    in_block = False
    last_pool = ""
    pool_stats: list[int] = []
    for line in section:
        if _WIN_DHCP_POOLS_STATS_TRANSLATE.get(line[0], line[0]) == "Subnet":
            in_block = True
            pool_stats = []
            last_pool = line[1]
            continue
        if in_block:
            pool_stats.append(_safe_int(line[1]))

        if len(pool_stats) == 3:
            in_block = False
            used, free, pending = pool_stats
            size = used + free + pending
            if size > 0 or params["empty_pools"]:
                yield Service(item=last_pool)


def check_win_dhcp_pools(item: str, params: Mapping[str, Any], section: Section) -> CheckResult:
    in_block = False
    pool_stats: list[int | None] = [None, None, None]
    for line in section:
        if _WIN_DHCP_POOLS_STATS_TRANSLATE.get(line[0], line[0]) == "Subnet" and line[1] == item:
            in_block = True
            pool_stats = []
            continue

        if in_block:
            pool_stats.append(_safe_int(line[1]))
            if len(pool_stats) == 3:
                break

    used, free, pending = pool_stats
    if used is None or free is None or pending is None:
        yield Result(state=State.UNKNOWN, summary="Pool information not found")
        return

    size = used + free + pending

    # Catch unused pools
    if size == 0:
        yield Result(
            state=State.UNKNOWN,
            summary="DHCP Pool contains no IP addresses / is deactivated",
        )
        return

    yield from check_dhcp_pools_levels(free, used, pending, size, params)
    yield Result(  # See SUP-9126
        state=State.OK,
        summary="Values are averaged",
        details=(
            "All values are averaged, as the Windows DHCP plug-in collects statistics, "
            "not real-time measurements"
        ),
    )


check_plugin_win_dhcp_pools = CheckPlugin(
    name="win_dhcp_pools",
    service_name="DHCP Pool %s",
    discovery_function=discover_win_dhcp_pools,
    discovery_default_parameters={"empty_pools": False},
    discovery_ruleset_name="discovery_win_dhcp_pools",
    check_function=check_win_dhcp_pools,
    check_default_parameters={"free_leases": (10.0, 5.0)},
    check_ruleset_name="win_dhcp_pools",
)

# .
#   .--Pool stats----------------------------------------------------------.
#   |              ____             _       _        _                     |
#   |             |  _ \ ___   ___ | |  ___| |_ __ _| |_ ___               |
#   |             | |_) / _ \ / _ \| | / __| __/ _` | __/ __|              |
#   |             |  __/ (_) | (_) | | \__ \ || (_| | |_\__ \              |
#   |             |_|   \___/ \___/|_| |___/\__\__,_|\__|___/              |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def discover_win_dhcp_pools_stats(section: Section) -> DiscoveryResult:
    if any(first_word for first_word, *_rest in section):
        yield Service()


def check_win_dhcp_pools_stats(section: Section) -> CheckResult:
    this_time = time.time()
    value_store = get_value_store()

    for line in section:
        if len(line) > 0:
            key = _WIN_DHCP_POOLS_STATS_TRANSLATE.get(line[0], line[0])
            if key in [
                "Discovers",
                "Offers",
                "Requests",
                "Acks",
                "Nacks",
                "Declines",
                "Releases",
                "Scopes",
            ]:
                value = _safe_int(line[1])
                yield from check_levels_v1(
                    get_rate(value_store, key, this_time, value),
                    metric_name=key,
                    render_func=lambda f: f"{f:.0f}/s",
                    label=key,
                )


check_plugin_win_dhcp_pools_stats = CheckPlugin(
    name="win_dhcp_pools_stats",
    service_name="DHCP Stats",
    sections=["win_dhcp_pools"],
    discovery_function=discover_win_dhcp_pools_stats,
    check_function=check_win_dhcp_pools_stats,
)
