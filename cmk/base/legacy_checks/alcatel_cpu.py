#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.lib.alcatel import DETECT_ALCATEL, DETECT_ALCATEL_AOS7


def parse_alcatel_cpu(string_table: StringTable) -> StringTable | None:
    return string_table or None


def inventory_alcatel_cpu(section):
    yield None, {}


def check_alcatel_cpu(_no_item, _no_params, section):
    cpu_perc = int(section[0][0])
    warn, crit = (90.0, 95.0)
    status = 0
    levelstext = ""
    if cpu_perc >= crit:
        status = 2
    elif cpu_perc >= warn:
        status = 1
    if status:
        levelstext = f" (warn/crit at {warn:.1f}%/{crit:.1f}%)"
    perfdata = [("util", cpu_perc, warn, crit, 0, 100)]
    return status, "total: %.1f%%" % cpu_perc + levelstext, perfdata


check_info["alcatel_cpu"] = LegacyCheckDefinition(
    parse_function=parse_alcatel_cpu,
    detect=DETECT_ALCATEL,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.6486.800.1.2.1.16.1.1.1",
        oids=["13"],
    ),
    service_name="CPU utilization",
    discovery_function=inventory_alcatel_cpu,
    check_function=check_alcatel_cpu,
)


check_info["alcatel_cpu_aos7"] = LegacyCheckDefinition(
    parse_function=parse_alcatel_cpu,
    detect=DETECT_ALCATEL_AOS7,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.6486.801.1.2.1.16.1.1.1.1.1",
        oids=["15"],
    ),
    service_name="CPU utilization",
    discovery_function=inventory_alcatel_cpu,
    check_function=check_alcatel_cpu,
)
