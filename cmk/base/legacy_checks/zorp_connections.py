#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Zorp FW - connections
This check displays individual connections returned by
  zorpctl szig -r zorp.stats.active_connections
It sums up all connections and checks against configurable maximum values.
"""


from cmk.base.check_api import check_levels, LegacyCheckDefinition
from cmk.base.config import check_info


def parse_zorp_connections(string_table):
    """Creates dict name -> connections
    from string_table =
    [["Instance <name>:", "walking"], ["zorp.stats.active_connections:", "<Number|'None'>"],
     ["Instance <name>:", "walking"], ["zorp.stats.active_connections:", "<Number|'None'>"],
     ...]
    """
    return {
        instance[1].rstrip(":"): int(state[1]) if state[1] != "None" else 0
        for instance, state in zip(string_table[::2], string_table[1::2])
    }


def check_zorp_connections(item, params, parsed):
    """List number of connections for each connection type and check against
    total number of connections"""
    if not parsed:
        return

    yield from ((0, "%s: %d" % elem) for elem in parsed.items())

    yield check_levels(
        sum(parsed.values()),
        "connections",
        params.get("levels"),
        infoname="Total connections",
        human_readable_func=int,
    )


def discover_zorp_connections(parsed):
    return [(None, {})]


check_info["zorp_connections"] = LegacyCheckDefinition(
    parse_function=parse_zorp_connections,
    service_name="Zorp Connections",
    discovery_function=discover_zorp_connections,
    check_function=check_zorp_connections,
    check_ruleset_name="zorp_connections",
    check_default_parameters={
        "levels": (15, 20),
    },
)
