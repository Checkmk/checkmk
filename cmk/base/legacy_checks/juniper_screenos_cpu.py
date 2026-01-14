#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import render, SNMPTree, StringTable
from cmk.plugins.juniper.lib import DETECT_JUNIPER_SCREENOS

check_info = {}


def discover_juniper_screenos_cpu(info):
    yield None, {}


def check_juniper_screenos_cpu(_no_item, params, info):
    util1, util15 = map(float, info[0])
    warn, crit = params.get("util", (None, None)) if isinstance(params, dict) else params

    # Report 1min utilization as informational
    yield check_levels(util1, "util1", None, human_readable_func=render.percent, infoname="1min")

    # Check levels on 15min utilization
    yield check_levels(
        util15, "util15", (warn, crit), human_readable_func=render.percent, infoname="15min"
    )


def parse_juniper_screenos_cpu(string_table: StringTable) -> StringTable | None:
    return string_table or None


check_info["juniper_screenos_cpu"] = LegacyCheckDefinition(
    name="juniper_screenos_cpu",
    parse_function=parse_juniper_screenos_cpu,
    detect=DETECT_JUNIPER_SCREENOS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3224.16.1",
        oids=["2", "4"],
    ),
    service_name="CPU utilization",
    discovery_function=discover_juniper_screenos_cpu,
    check_function=check_juniper_screenos_cpu,
    check_ruleset_name="cpu_utilization",
    check_default_parameters={"util": (80.0, 90.0)},
)
