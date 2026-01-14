#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import render, SNMPTree, StringTable
from cmk.plugins.emc.lib import DETECT_ISILON

check_info = {}


def discover_emc_isilon_cpu_utilization(info):
    # the device reports cpu utilization for each core and a total. This interprets only the total
    return [(None, {})]


def check_emc_isilon_cpu_utilization(item, params, info):
    # expecting only one line because why would there be multiple totals?
    for line in info:
        # all utilizations are in per mil
        # grouping user+nice and system+interrupt, the same way cpu_util.include does
        user_perc = (int(line[0]) + int(line[1])) * 0.1
        system_perc = int(line[2]) * 0.1
        interrupt_perc = int(line[3]) * 0.1
        total_perc = user_perc + system_perc + interrupt_perc

        for utype, value in (
            ("user", user_perc),
            ("system", system_perc),
            ("interrupt", interrupt_perc),
        ):
            yield check_levels(
                value,
                utype,
                None,
                human_readable_func=render.percent,
                infoname=utype.title(),
            )

        levels = params if not isinstance(params, dict) else params.get("util")
        yield check_levels(
            total_perc,
            None,
            levels,
            human_readable_func=render.percent,
            infoname="Total",
        )


def parse_emc_isilon_cpu(string_table: StringTable) -> StringTable | None:
    return string_table or None


check_info["emc_isilon_cpu"] = LegacyCheckDefinition(
    name="emc_isilon_cpu",
    parse_function=parse_emc_isilon_cpu,
    detect=DETECT_ISILON,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12124.2.2.3",
        oids=["1", "2", "3", "4"],
    ),
    service_name="Node CPU utilization",
    discovery_function=discover_emc_isilon_cpu_utilization,
    check_function=check_emc_isilon_cpu_utilization,
    check_ruleset_name="cpu_utilization",
)
