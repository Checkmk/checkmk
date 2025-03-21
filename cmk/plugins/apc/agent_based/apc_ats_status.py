#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping

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
from cmk.plugins.apc.lib.apc_ats import (
    CommunictionStatus,
    OverCurrentStatus,
    PowerSupplyStatus,
    RedunandancyStatus,
    Source,
    Status,
)
from cmk.plugins.lib.apc import DETECT_ATS


def parse_apc_ats_status(info: StringTable) -> Status | None:
    if len(info) == 1:
        return Status.from_raw(info[0])
    return None


def discover_apc_ats_status(section: Status) -> DiscoveryResult:
    if section and section.selected_source:
        yield Service(parameters={"power_source": section.selected_source.value})


def check_apc_ats_status(params: Mapping[str, object], section: Status) -> CheckResult:
    source = params["power_source"]

    # current source of power
    source_parsed = Source(source)
    if source_parsed != section.selected_source:
        assert section.selected_source is not None
        yield Result(
            state=State.CRIT,
            summary=f"Power source Changed from {source_parsed.name} to {section.selected_source.name}",
        )
    else:
        yield Result(state=State.OK, summary=f"Power source {source_parsed.name} selected")

    # current communication status of the Automatic Transfer Switch.
    if section.com_status == CommunictionStatus.NeverDiscovered:
        yield Result(state=State.WARN, summary="Communication Status: never Discovered")
    elif section.com_status == CommunictionStatus.Lost:
        yield Result(state=State.CRIT, summary="Communication Status: lost")

    # current redundancy state of the ATS.
    # Lost(1) indicates that the ATS is unable to switch over to the alternate power source
    # if the current source fails. Redundant(2) indicates that the ATS will switch
    # over to the alternate power source if the current source fails.
    if section.redundancy == RedunandancyStatus.Lost:
        yield Result(state=State.CRIT, summary="redundancy lost")
    else:
        yield Result(state=State.OK, summary="Device fully redundant")

    # current state of the ATS. atsOverCurrent(1) indicates that the ATS has i
    # exceeded the output current threshold and will not allow a switch
    # over to the alternate power source if the current source fails.
    # atsCurrentOK(2) indicates that the output current is below the output current threshold.
    if section.overcurrent == OverCurrentStatus.Exceeded:
        yield Result(state=State.CRIT, summary="exceeded output current threshold")

    for powersource in section.powersources:
        if powersource is None:
            continue
        match powersource.status:
            case PowerSupplyStatus.Failure:
                yield Result(state=State.CRIT, summary=f"{powersource.name} power supply failed")
            case PowerSupplyStatus.NotAvailable:
                # The MIB only defines two valid values "1" and "2". But in reality, the SNMP file
                # may contain a value of "0", too. According to SUP-22815 this case is OK, too.
                yield Result(
                    state=State.OK, summary=f"{powersource.name} power supply not available"
                )


snmp_section_apc_ats_status = SimpleSNMPSection(
    name="apc_ats_status",
    detect=DETECT_ATS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.318.1.1.8.5.1",
        oids=["1.0", "2.0", "3.0", "4.0", "5.0", "6.0", "17.0", "18.0"],
    ),
    parse_function=parse_apc_ats_status,
)
check_plugin_apc_ats_status = CheckPlugin(
    name="apc_ats_status",
    service_name="ATS Status",
    discovery_function=discover_apc_ats_status,
    check_function=check_apc_ats_status,
    check_default_parameters={},
)
