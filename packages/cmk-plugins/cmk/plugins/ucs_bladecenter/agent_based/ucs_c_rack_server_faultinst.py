#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# exemplary output of special agent agent_ucs_bladecenter (<TAB> is tabulator):
#
# <<<ucs_c_rack_server_faultinst:sep(9)>>>
# faultInst<TAB>severity critical<TAB>cause powerproblem<TAB>code F0883<TAB>descr Power supply 4 is in a degraded state, or has bad input voltage<TAB>affectedDN sys/rack-unit-1/psu-4
# faultInst<TAB>severity major<TAB>cause psuRedundancyFail<TAB>code F0743<TAB>descr Power Supply redundancy is lost : Reseat or replace Power Supply <TAB>affectedDN sys/rack-unit-1/psu
# faultInst<TAB>severity major<TAB>cause equipmentDegraded<TAB>code F0969<TAB>descr Storage Raid Battery 11 Degraded: please check the battery or the storage controller<TAB>affectedDN sys/rack-unit-1/board/storage-SAS-SLOT-SAS/raid-battery-11
# faultInst<TAB>severity major<TAB>cause equipmentInoperable<TAB>code F0531<TAB>descr Storage Raid Battery 11 is inoperable: Check Controller battery<TAB>affectedDN sys/rack-unit-1/board/storage-SAS-SLOT-SAS/raid-battery-11

import collections
from collections.abc import Mapping, Sequence

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
    StringTable,
)
from cmk.plugins.ucs_bladecenter import lib as ucs_bladecenter


def parse_ucs_c_rack_server_faultinst(string_table: StringTable) -> Mapping[str, Sequence[str]]:
    """
    >>> parse_ucs_c_rack_server_faultinst([['faultInst', 'severity critical', 'cause powerproblem', 'code F0883', 'descr Broken', 'affectedDN sys/rack-unit-1/psu-4']])
    {'Severity': ['critical'], 'Cause': ['powerproblem'], 'Code': ['F0883'], 'Description': ['Broken'], 'Affected DN': ['rack-unit-1/psu-4']}
    >>> parse_ucs_c_rack_server_faultinst([])
    {}
    """
    parsed: dict[str, list[str]] = {}
    key_translation = {"descr": "Description", "affectedDN": "Affected DN"}

    for fault_inst_data in string_table:
        for data in fault_inst_data[1:]:
            key, value = data.split(" ", 1)
            key = key_translation.get(key, key.capitalize())
            parsed.setdefault(key, []).append(value)

        parsed["Affected DN"][-1] = parsed["Affected DN"][-1].replace("sys/", "")

    return parsed


agent_section_ucs_c_rack_server_faultinst = AgentSection(
    name="ucs_c_rack_server_faultinst",
    parse_function=parse_ucs_c_rack_server_faultinst,
)


def check_ucs_c_rack_server_faultinst(section: Mapping[str, Sequence[str]]) -> CheckResult:
    if not section:
        yield Result(state=State.OK, summary="No fault instances found")
        return

    states = [
        ucs_bladecenter.UCS_FAULTINST_SEVERITY_TO_STATE.get(severity, State.UNKNOWN)
        for severity in section["Severity"]
    ]
    overall_state = State.worst(*states)

    # report overall state and summary of fault instances
    severity_counter = collections.Counter(section["Severity"])
    yield Result(
        state=overall_state,
        summary="Found faults: "
        + ", ".join(
            [
                f"{severity_counter[severity]} with severity '{severity}'"
                for severity in sorted(severity_counter.keys())
            ]
        ),
    )

    # report individual faults sorted by monitoring state
    start_str = "Individual faults: "
    for index in sorted(range(len(states)), key=lambda idx: int(states[idx])):
        yield Result(
            state=states[index],
            notice=start_str
            + ", ".join(
                [
                    f"{key}: {section[key][index]}"
                    for key in ["Severity", "Description", "Cause", "Code", "Affected DN"]
                ]
            ),
        )
        start_str = ""


def discover_ucs_c_rack_server_faultinst(section: Mapping[str, Sequence[str]]) -> DiscoveryResult:
    yield Service()


check_plugin_ucs_c_rack_server_faultinst = CheckPlugin(
    name="ucs_c_rack_server_faultinst",
    service_name="Fault Instances Rack",
    discovery_function=discover_ucs_c_rack_server_faultinst,
    check_function=check_ucs_c_rack_server_faultinst,
)
