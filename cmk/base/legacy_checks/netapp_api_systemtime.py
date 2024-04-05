#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# 7 mode
# <<<netapp_api_systemtime:sep(9)>>>
# name 76123    123

# Cluster mode
# <<<netapp_api_systemtime:sep(9)>>>
# node1 76123   123123
# node2 7612311 123123


import collections

from cmk.base.check_api import check_levels, get_age_human_readable, LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import render

NetappApiTimeEntry = collections.namedtuple(  # pylint: disable=collections-namedtuple-call
    "NetappApiTimeEntry",
    [
        "agent_time",
        "system_time",
    ],
)


def parse_netapp_api_systemtime(string_table):
    parsed = {}
    for line in string_table:
        try:
            item, agent_time, system_time = line
            parsed[item] = NetappApiTimeEntry(int(agent_time), int(system_time))
        except ValueError:
            pass
    return parsed


def check_netapp_api_systemtime(item, params, parsed):
    if not (entry := parsed.get(item)):
        return
    yield check_levels(
        entry.system_time,
        None,
        None,
        infoname="System time",
        human_readable_func=render.datetime,
    )
    yield check_levels(
        entry.agent_time - entry.system_time,
        "time_difference",
        params.get("levels", (None, None)),
        infoname="Time difference",
        human_readable_func=get_age_human_readable,
    )


def discover_netapp_api_systemtime(section):
    yield from ((item, {}) for item in section)


check_info["netapp_api_systemtime"] = LegacyCheckDefinition(
    parse_function=parse_netapp_api_systemtime,
    service_name="Systemtime %s",
    discovery_function=discover_netapp_api_systemtime,
    check_function=check_netapp_api_systemtime,
    check_ruleset_name="netapp_systemtime",
)
