#!/usr/bin/env python3
# author: Oguzhan Cicek, OpenSource Security GmbH - oguzhan(at)os-s.de

# Example Input:
#[...]
#.1.3.6.1.4.1.12356.118.3.1.1.0 v2.52-build0340 (GA)
#.1.3.6.1.4.1.12356.118.3.1.2.0 2
#.1.3.6.1.4.1.12356.118.3.1.3.0 4
#.1.3.6.1.4.1.12356.118.3.1.4.0 260459760
#.1.3.6.1.4.1.12356.118.3.1.5.0 710698
#.1.3.6.1.4.1.12356.118.3.1.6.0 3754417
#.1.3.6.1.4.1.12356.118.3.1.7.0 2
#.1.3.6.1.4.1.12356.118.3.1.8.0 32908349
#.1.3.6.1.4.1.12356.118.3.2.1.0 5.2.50534
#.1.3.6.1.4.1.12356.118.3.2.2.0 2.4.20034
#.1.3.6.1.4.1.12356.118.3.2.3.0 3.2.279
#.1.3.6.1.4.1.12356.118.3.2.4.0 4.478
#.1.3.6.1.4.1.12356.118.3.2.5.0 14.613
#[...]

# Example GUI Output:
# OK	FortiSandbox SW: Tracer engine
#       Software: Tracer engine, Version: 5.2.50534
# OK	FortiSandbox SW: Rating engine
#       Software: Rating engine, Version: 2.4.20034
# OK	FortiSandbox SW: System tools
#       Software: System tools, Version: 3.2.279
# OK	FortiSandbox SW: Sniffer
#       Software: Sniffer, Version: 4.478
# OK	FortiSandbox SW: Network alerts singature database
#       Software: Network alerts signature database, Version: 14.613

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
    equals,
    SNMPTree,
)
from typing import List

Section = List[List[str]]


def parse_fortisandbox_software(string_table: List[StringTable]) -> Section:
    parsed = [["Tracer engine", string_table[0][0][0]], ["Rating engine", string_table[0][0][1]],
              ["System tools", string_table[0][0][2]], ["Sniffer", string_table[0][0][3]],
              ["Network alerts signature database", string_table[0][0][4]],
              ["Android analytic engine", string_table[0][0][5]],
              ["Android rating engine", string_table[0][0][6]]]
    return parsed


def discovery_fortisandbox_software(section: Section) -> DiscoveryResult:
    for sw in section:
        if sw[1] != "":
            yield Service(item=sw[0])


def check_fortisandbox_software(item: str, section: Section) -> CheckResult:
    for sw in section:
        if sw[0] == item:
            yield Result(state=State.OK, summary="Software: %s, Version: %s" % (item, sw[1]))


register.snmp_section(
    name="fortisandbox_software",
    detect=equals('.1.3.6.1.2.1.1.2.0', '.1.3.6.1.4.1.12356.118.1.30006'),
    parse_function=parse_fortisandbox_software,
    fetch=[
        SNMPTree(
            base='.1.3.6.1.4.1.12356.118.3.2',
            oids=[
                '1',  # fsaSysTracer
                '2',  # fsaSysRating
                '3',  # fsaSysTool
                '4',  # fsaSysSniffer
                '5',  # fsaSysIPS
                '6',  # fsaSysAndroidA
                '7',  # fsaSysAndroidR
            ]),
    ],
)

register.check_plugin(
    name="fortisandbox_software",
    service_name="FortiSandbox SW: %s",
    discovery_function=discovery_fortisandbox_software,
    check_function=check_fortisandbox_software,
)
