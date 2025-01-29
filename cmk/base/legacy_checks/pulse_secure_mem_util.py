#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Mapping

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import render, SNMPTree, StringTable
from cmk.plugins.lib import pulse_secure

check_info = {}

Section = Mapping[str, int]

METRICS_INFO_NAMES_PULSE_SECURE_MEM = (
    ["mem_used_percent", "swap_used_percent"],
    ["RAM used", "Swap used"],
)


def parse_pulse_secure_mem(string_table: StringTable) -> Section | None:
    return pulse_secure.parse_pulse_secure(string_table, *METRICS_INFO_NAMES_PULSE_SECURE_MEM[0])


def discover_pulse_secure_mem_util(section: Section) -> Iterable[tuple[None, dict]]:
    if section:
        yield None, {}


def check_pulse_secure_mem(item, params, parsed):
    if not parsed:
        return

    for metric, info_name in zip(*METRICS_INFO_NAMES_PULSE_SECURE_MEM):
        if metric in parsed:
            yield check_levels(
                parsed[metric],
                metric,
                params.get(metric),
                infoname=info_name,
                human_readable_func=render.percent,
            )


check_info["pulse_secure_mem_util"] = LegacyCheckDefinition(
    name="pulse_secure_mem_util",
    detect=pulse_secure.DETECT_PULSE_SECURE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12532",
        oids=["11", "24"],
    ),
    parse_function=parse_pulse_secure_mem,
    service_name="Pulse Secure IVE memory utilization",
    discovery_function=discover_pulse_secure_mem_util,
    check_function=check_pulse_secure_mem,
    check_ruleset_name="pulse_secure_mem_util",
    check_default_parameters={
        "mem_used_percent": (90, 95),
        "swap_used_percent": (5, 101),
    },
)
