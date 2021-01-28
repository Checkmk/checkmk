#!/usr/bin/env python3
# author: Oguzhan Cicek, OpenSource Security GmbH - oguzhan(at)os-s.de

#Example Input:
#.1.3.6.1.2.1.1.1.0 testname
#.1.3.6.1.2.1.1.2.0 .1.3.6.1.4.1.12356.101.1.15000
#[...]
#.1.3.6.1.4.1.12356.101.13.1.1.0 3
#.1.3.6.1.4.1.12356.101.13.1.2.0 11
#.1.3.6.1.4.1.12356.101.13.1.3.0 128
#.1.3.6.1.4.1.12356.101.13.1.4.0 2
#.1.3.6.1.4.1.12356.101.13.1.5.0 2
#.1.3.6.1.4.1.12356.101.13.1.6.0 4
#.1.3.6.1.4.1.12356.101.13.1.7.0 test
#.1.3.6.1.4.1.12356.101.13.2.1.1.1.1 1
#[...]

#Example GUI Output:
#OK	Fortigate High Availability
#       System Mode: activePassive, Priority: 128, Schedule= roundRobin,
#       Group Id: 11, Group Name: test

from .agent_based_api.v1.type_defs import (
    DiscoveryResult,
    CheckResult,
    StringTable,
)
from .agent_based_api.v1 import (
    register,
    Result,
    State,
    Service,
    startswith,
    SNMPTree,
)
from typing import List

Section = List[str]


def parse_fortigate_ha(string_table: List[StringTable]) -> Section:
    return string_table[0][0]


def discovery_fortigate_ha(section: Section) -> DiscoveryResult:
    yield Service()


def check_fortigate_ha(section: Section) -> CheckResult:
    gid = section[1]
    prio = section[2]
    gname = section[4]
    mode_code = int(section[0])
    system_modes = {
        1: 'standalone',
        2: 'activeActive',
        3: 'activePassive',
    }
    mode = system_modes[mode_code]
    sched_code = int(section[3])
    lbsched_modes = {
        1: 'none',
        2: 'hub',
        3: 'leastConnections',
        4: 'roundRobin',
        5: 'weightedRoundRobin',
        6: 'random',
        7: 'ipBased',
        8: 'ipPortBased',
    }
    sched = lbsched_modes[sched_code]
    status = "System Mode: %s, Priority: %s, Schedule= %s, Group Id: %s, Group Name: %s" % (
        mode, prio, sched, gid, gname)
    yield Result(state=State.OK, summary=status)


register.snmp_section(
    name="fortigate_ha",
    parse_function=parse_fortigate_ha,
    detect=startswith('.1.3.6.1.2.1.1.2.0', '.1.3.6.1.4.1.12356.101.1.'),
    fetch=[
        SNMPTree(
            base='.1.3.6.1.4.1.12356.101.13.1',
            oids=[
                '1',  # fgHaSystemMode
                '2',  # fgHaGroupId
                '3',  # fgHaPriority
                '6',  # fgHaSchedule
                '7',  # fgHaGroupName
            ]),
    ],
)

register.check_plugin(
    name="fortigate_ha",
    service_name="Fortigate High Availability",
    discovery_function=discovery_fortigate_ha,
    check_function=check_fortigate_ha,
)
