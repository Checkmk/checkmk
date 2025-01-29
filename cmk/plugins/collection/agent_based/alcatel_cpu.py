#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.alcatel import DETECT_ALCATEL, DETECT_ALCATEL_AOS7


def parse_alcatel_cpu(string_table: StringTable) -> float | None:
    return int(string_table[0][0]) if string_table else None


def inventory_alcatel_cpu(section: float) -> DiscoveryResult:
    yield Service()


def check_alcatel_cpu(section: float) -> CheckResult:
    yield from check_levels(
        section,
        metric_name="util",
        levels_upper=("fixed", (90.0, 95.0)),
        label="Total",
        render_func=render.percent,
    )


snmp_section_alcatel_cpu = SimpleSNMPSection(
    name="alcatel_cpu",
    detect=DETECT_ALCATEL,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.6486.800.1.2.1.16.1.1.1",
        oids=["13"],
    ),
    parse_function=parse_alcatel_cpu,
)
check_plugin_alcatel_cpu = CheckPlugin(
    name="alcatel_cpu",
    service_name="CPU utilization",
    discovery_function=inventory_alcatel_cpu,
    check_function=check_alcatel_cpu,
)
snmp_section_alcatel_cpu_aos7 = SimpleSNMPSection(
    name="alcatel_cpu_aos7",
    detect=DETECT_ALCATEL_AOS7,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.6486.801.1.2.1.16.1.1.1.1.1",
        oids=["15"],
    ),
    parse_function=parse_alcatel_cpu,
)
check_plugin_alcatel_cpu_aos7 = CheckPlugin(
    name="alcatel_cpu_aos7",
    service_name="CPU utilization",
    discovery_function=inventory_alcatel_cpu,
    check_function=check_alcatel_cpu,
)
