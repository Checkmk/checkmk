#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import json
from collections.abc import Iterable, Mapping

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import render

check_info = {}

Section = Mapping[str, float]


def parse_cadvisor_cpu(string_table):
    cpu_info = json.loads(string_table[0][0])
    parsed = {}
    for cpu_name, cpu_entries in cpu_info.items():
        if len(cpu_entries) != 1:
            continue
        try:
            parsed[cpu_name] = float(cpu_entries[0]["value"])
        except KeyError:
            continue
    return parsed


def discover_cadvisor_cpu(section: Section) -> Iterable[tuple[None, dict]]:
    if section:
        yield None, {}


def check_cadvisor_cpu(_item, params, parsed):
    # No suitable function in cpu_util.include
    cpu_user = parsed["cpu_user"]
    cpu_system = parsed["cpu_system"]
    cpu_total = cpu_user + cpu_system

    yield check_levels(cpu_user, "user", None, human_readable_func=render.percent, infoname="User")
    yield check_levels(
        cpu_system,
        "system",
        None,
        human_readable_func=render.percent,
        infoname="System",
    )
    yield check_levels(
        cpu_total,
        "util",
        params.get("util"),
        human_readable_func=render.percent,
        infoname="Total CPU",
    )


check_info["cadvisor_cpu"] = LegacyCheckDefinition(
    name="cadvisor_cpu",
    parse_function=parse_cadvisor_cpu,
    service_name="CPU utilization",
    discovery_function=discover_cadvisor_cpu,
    check_function=check_cadvisor_cpu,
    check_ruleset_name="cpu_utilization",
)
