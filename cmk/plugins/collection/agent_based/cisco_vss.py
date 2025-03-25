#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Example SNMP walk (extract)
# All names OIDs are prefixed with CISCO-VIRTUAL-SWITCH-MIB::
# All numeric OIDs are prefixed with .1.3.6.1.4.1.9.9.388

# cvsDomain.0                            .1.1.1.0 10
# cvsSwitchID.0                          .1.1.2.0 1
# cvsSwitchCapability.0                  .1.1.3.0 "C0 "
# cvsSwitchMode.0                        .1.1.4.0 2
# cvsSwitchConvertingStatus.0            .1.1.5.0 2
# cvsVSLChangeNotifEnable.0              .1.1.6.0 2
# cvsCoreSwitchPriority.1                .1.2.1.1.2.1 100
# cvsCoreSwitchPriority.2                .1.2.1.1.2.2 100
# cvsCoreSwitchPreempt.1                 .1.2.1.1.3.1 2
# cvsCoreSwitchPreempt.2                 .1.2.1.1.3.2 2
# cvsCoreSwitchLocation.1                .1.2.1.1.4.1
# cvsCoreSwitchLocation.2                .1.2.1.1.4.2
# cvsChassisSwitchID.2                   .1.2.2.1.1.2 1
# cvsChassisSwitchID.500                 .1.2.2.1.1.500 2
# cvsChassisRole.2                       .1.2.2.1.2.2 2
# cvsChassisRole.500                     .1.2.2.1.2.500 3
# cvsChassisUpTime.2                     .1.2.2.1.3.2 184371004
# cvsChassisUpTime.500                   .1.2.2.1.3.500 184371004
# cvsVSLCoreSwitchID.41                  .1.3.1.1.2.41 1
# cvsVSLCoreSwitchID.42                  .1.3.1.1.2.42 2
# cvsVSLConnectOperStatus.41             .1.3.1.1.3.41 1
# cvsVSLConnectOperStatus.42             .1.3.1.1.3.42 1
# cvsVSLLastConnectionStateChange.41     .1.3.1.1.4.41 "07 DE 07 18 01 12 22 00 "
# cvsVSLLastConnectionStateChange.42     .1.3.1.1.4.42 "07 DE 07 18 01 12 22 00 "
# cvsVSLConfiguredPortCount.41           .1.3.1.1.5.41 2
# cvsVSLConfiguredPortCount.42           .1.3.1.1.5.42 2
# cvsVSLOperationalPortCount.41          .1.3.1.1.6.41 2
# cvsVSLOperationalPortCount.42          .1.3.1.1.6.42 2
# cvsVSLConnectionRowStatus.41           .1.3.1.1.7.41 1
# cvsVSLConnectionRowStatus.42           .1.3.1.1.7.42 1
# cvsModuleVSSupported.1000              .1.4.1.1.1.1000 1
# cvsModuleVSSupported.11000             .1.4.1.1.1.11000 1
# cvsModuleVSLCapable.1000               .1.4.1.1.2.1000 1
# cvsModuleVSLCapable.11000              .1.4.1.1.2.11000 1
# cvsModuleSlotNumber.1000               .1.4.1.1.3.1000 1
# cvsModuleSlotNumber.11000              .1.4.1.1.3.11000 11
# cvsModuleRprWarm.1000                  .1.4.1.1.4.1000 1
# cvsModuleRprWarm.11000                 .1.4.1.1.4.11000 1
# cvsDualActiveDetectionNotifEnable.0    .1.5.1.0 2


from collections.abc import Sequence

from cmk.agent_based.v2 import (
    all_of,
    any_of,
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    exists,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)

cisco_vss_role_names = {
    "1": "standalone",
    "2": "active",
    "3": "standby",
}

cisco_vss_operstatus_names = {
    "1": "up",
    "2": "down",
}


def inventory_cisco_vss(section: Sequence[StringTable]) -> DiscoveryResult:
    for _switch_id, chassis_role in section[0]:
        if chassis_role in ["2", "3"]:  # active, standby
            yield Service()


def check_cisco_vss(section: Sequence[StringTable]) -> CheckResult:
    chassis, ports = section
    for switch_id, chassis_role in chassis:
        if chassis_role == "1":
            state = State.CRIT
        else:
            state = State.OK
        yield Result(
            state=state, summary=f"chassis {switch_id}: {cisco_vss_role_names[chassis_role]}"
        )

    yield Result(state=State.OK, summary="%d VSL connections configured" % len(ports))

    for core_switch_id, operstatus, conf_portcount, op_portcount in ports:
        if operstatus == "1":
            state = State.OK
        else:
            state = State.CRIT
        yield Result(
            state=state,
            summary=f"core switch {core_switch_id}: VSL {cisco_vss_operstatus_names[operstatus]}",
        )

        if conf_portcount == op_portcount:
            state = State.OK
        else:
            state = State.CRIT
        yield Result(state=state, summary=f"{op_portcount}/{conf_portcount} ports operational")


def parse_cisco_vss(string_table: Sequence[StringTable]) -> Sequence[StringTable]:
    return string_table


snmp_section_cisco_vss = SNMPSection(
    name="cisco_vss",
    detect=all_of(
        any_of(
            contains(".1.3.6.1.2.1.1.1.0", "Catalyst 45"),
            contains(".1.3.6.1.2.1.1.1.0", "Catalyst 65"),
            contains(".1.3.6.1.2.1.1.1.0", "s72033_rp"),
        ),
        exists(".1.3.6.1.4.1.9.9.388.1.1.1.0"),
    ),
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.9.9.388.1.2.2.1",
            oids=["1", "2"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.9.9.388.1.3.1.1",
            oids=["2", "3", "5", "6"],
        ),
    ],
    parse_function=parse_cisco_vss,
)


check_plugin_cisco_vss = CheckPlugin(
    name="cisco_vss",
    service_name="VSS Status",
    discovery_function=inventory_cisco_vss,
    check_function=check_cisco_vss,
)
