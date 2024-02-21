#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)

from .lib import DETECT_PEAKFLOW_TMS, DETECT_PRAVAIL


def parse_arbor_host_fault(string_table: StringTable) -> str | None:
    return string_table[0][0] if string_table else None


snmp_section_arbor_peakflow_tms_host_fault = SimpleSNMPSection(
    name="arbor_peakflow_tms_host_fault",
    detect=DETECT_PEAKFLOW_TMS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9694.1.5.2",
        oids=["1.0"],
    ),
    parse_function=parse_arbor_host_fault,
)


snmp_section_arbor_pravail_host_fault = SimpleSNMPSection(
    name="arbor_pravail_host_fault",
    detect=DETECT_PRAVAIL,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9694.1.6.2",
        oids=["1.0"],
    ),
    parse_function=parse_arbor_host_fault,
)


def discover_arbor_host_fault(section: str) -> DiscoveryResult:
    yield Service()


def check_arbor_host_fault(section: str) -> CheckResult:
    yield Result(state=State.OK if section == "No Fault" else State.CRIT, summary=section)


check_plugin_arbor_peakflow_tms_host_fault = CheckPlugin(
    name="arbor_peakflow_tms_host_fault",
    service_name="Host Fault",
    discovery_function=discover_arbor_host_fault,
    check_function=check_arbor_host_fault,
)


check_plugin_arbor_pravail_host_fault = CheckPlugin(
    name="arbor_pravail_host_fault",
    service_name="Host Fault",
    discovery_function=discover_arbor_host_fault,
    check_function=check_arbor_host_fault,
)
