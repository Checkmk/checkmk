#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Mapping

from .agent_based_api.v1 import check_levels, register, Service
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable

ParsedSection = Mapping[int, int]

# Example output from agent:
# <<<winperf_msx_queues>>>
# 12947176002.19
# 1 instances: _total
# 10334 0 rawcount
# 10336 810 rawcount
# 10338 0 rawcount
# 10340 0 rawcount
# 10342 0 rawcount
# 10344 0 rawcount
# 10346 810 rawcount
# 10348 810 rawcount
# 10350 821 rawcount
# 10352 821 counter
# 10354 10 rawcount
# 10356 10 counter
# 10358 0 rawcount
# 10360 0 rawcount
# 10362 0 rawcount
# 10364 811 rawcount


# Example output from a Exchange 2013 server:
# <<<winperf_msx_queues>>>
# 1385554029.05 12048
# 4 instances: niedrige_priorität normale_priorität hohe_priorität _total
# 2 0 0 0 0 rawcount
# 4 0 0 0 0 rawcount
# 6 0 0 0 0 rawcount
def parse_winperf_msx_queues(string_table: StringTable) -> ParsedSection:
    num_instances = int(string_table[1][0])
    if num_instances == 0:
        return {}
    return {int(line[0]): int(line[-2]) for line in string_table[2:]}


register.agent_section(
    name="winperf_msx_queues",
    parse_function=parse_winperf_msx_queues,
)


def discover_winperf_msx_queues(
    params: Mapping[str, Any],
    section: ParsedSection,
) -> DiscoveryResult:
    for item_name, offset in params["queue_names"]:
        if offset in section:
            yield Service(item=item_name, parameters={"offset": offset})


def check_winperf_msx_queues(
    item: str,
    params: Mapping[str, Any],
    section: ParsedSection,
) -> CheckResult:
    length = section.get(params["offset"])
    if length is not None:
        yield from check_levels(
            length,
            levels_upper=params.get("levels"),
            metric_name="length",
            render_func=str,
            label="Length",
        )


_DEFAULT_LEVELS = (500, 2000)
_DEFAULT_DISCOVERY_PARAMETERS = {
    "queue_names": [
        ("Active Remote Delivery", 2),
        ("Retry Remote Delivery", 4),
        ("Active Mailbox Delivery", 6),
        ("Poison Queue Length", 44),
    ]
}

register.check_plugin(
    name="winperf_msx_queues",
    service_name="Queue %s",
    discovery_default_parameters=_DEFAULT_DISCOVERY_PARAMETERS,
    discovery_ruleset_name="winperf_msx_queues_inventory",
    discovery_function=discover_winperf_msx_queues,
    check_default_parameters={
        "levels": _DEFAULT_LEVELS,
    },
    check_ruleset_name="msx_queues",
    check_function=check_winperf_msx_queues,
)
