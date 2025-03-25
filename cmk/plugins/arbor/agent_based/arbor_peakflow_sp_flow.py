#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)

from .lib import DETECT_PEAKFLOW_SP


def parse_peakflow_sp_flows(string_table: StringTable) -> int | None:
    return int(string_table[0][0]) if string_table else None


snmp_section_arbor_peakflow_sp_flow = SimpleSNMPSection(
    name="arbor_peakflow_sp_flows",
    detect=DETECT_PEAKFLOW_SP,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9694.1.4.2.1",
        oids=["12.0"],
    ),
    parse_function=parse_peakflow_sp_flows,
)


def discover_arbor_peakflow_sp_flows(section: int) -> DiscoveryResult:
    yield Service()


def check_arbor_peakflow_sp_flows(section: int) -> CheckResult:
    yield from check_levels_v1(section, metric_name="flows", label="Flows", render_func=str)


check_plugin_arbor_peakflow_sp_flows = CheckPlugin(
    name="arbor_peakflow_sp_flows",
    service_name="Flow Count",
    discovery_function=discover_arbor_peakflow_sp_flows,
    check_function=check_arbor_peakflow_sp_flows,
)
