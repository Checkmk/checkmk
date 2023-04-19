#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping

from .agent_based_api.v1 import register, Service
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils import uptime

Section = Mapping[str, uptime.Section]


def parse_couchbase_uptime(string_table: StringTable) -> Section:
    parsed = {}
    for line in string_table:
        if len(line) < 2:
            continue
        uptime_value, node = line[0], " ".join(line[1:])
        try:
            parsed[node] = uptime.Section(float(uptime_value), None)
        except ValueError:
            continue
    return parsed


register.agent_section(
    name="couchbase_nodes_uptime",
    parse_function=parse_couchbase_uptime,
)


def discover_couchbase_nodes_uptime(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_couchbase_nodes_uptime(
    item: str, params: Mapping[str, Any], section: Section
) -> CheckResult:
    if (uptime_section := section.get(item)) is None:
        return
    yield from uptime.check(params, uptime_section)


register.check_plugin(
    name="couchbase_nodes_uptime",
    service_name="Couchbase %s Uptime",
    discovery_function=discover_couchbase_nodes_uptime,
    check_function=check_couchbase_nodes_uptime,
    check_ruleset_name="uptime_multiitem",
    check_default_parameters={},
)
