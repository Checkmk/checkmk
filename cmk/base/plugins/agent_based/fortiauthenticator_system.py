#!/usr/bin/env python3
# author: Oguzhan Cicek, OpenSource Security GmbH - oguzhan(at)os-s.de

#Example Input:
#.1.3.6.1.2.1.1.1.0 testname
#.1.3.6.1.2.1.1.2.0 .1.3.6.1.4.1.8072.3.2.10
#[...]
#.1.3.6.1.4.1.8072.1.3.2.1.0 0
#.1.3.6.1.4.1.12356.100.1.1.1.0 FAC-VMTM1234567890
#.1.3.6.1.4.1.12356.100.1.2.1.0 1
#.1.3.6.1.4.1.12356.100.1.2.100.1.0 -1
#.1.3.6.1.4.1.12356.113.1.1.0 FACVM
#.1.3.6.1.4.1.12356.113.1.2.0 FAC-VMTM1234567890
#.1.3.6.1.4.1.12356.113.1.3.0 v5.5.0-build0366
#.1.3.6.1.4.1.12356.113.1.4.0 3
#.1.3.6.1.4.1.12356.113.1.5.0 28
#.1.3.6.1.4.1.12356.113.1.6.0 1
#.1.3.6.1.4.1.12356.113.1.201.1.0 255
#[...]

#Example GUI Output:
#OK	FortiAuthenticator System
#       Model: FACVM, Serial: FAC-VMTM1234567890, Version: v5.5.0-build0366,
#       HA Status: disabled

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

Section = List[str]


def parse_fortiauthenticator_system(string_table: List[StringTable]) -> Section:
    return string_table[0][0]


def discovery_fortiauthenticator_system(section: Section) -> DiscoveryResult:
    yield Service()


def check_fortiauthenticator_system(section: Section) -> CheckResult:
    model = section[0]
    serial = section[1]
    version = section[2]
    ha_status_code = int(section[3])
    ha_codes = {
        1: 'unknownOrDetermining',
        2: 'clusterMaster',
        3: 'clusterSlave',
        4: 'standaloneMaster',
        5: 'loadBalancingSlave',
        255: 'disabled'
    }
    ha_status = ha_codes[ha_status_code]
    status = "Model: %s, Serial: %s, Version: %s, HA Status: %s" % (model, serial, version,
                                                                    ha_status)
    yield Result(state=State.OK, summary=status)


register.snmp_section(
    name="fortiauthenticator_system",
    parse_function=parse_fortiauthenticator_system,
    detect=equals('.1.3.6.1.2.1.1.2.0', '.1.3.6.1.4.1.8072.3.2.10'),
    fetch=[
        SNMPTree(
            base='.1.3.6.1.4.1.12356.113.1',
            oids=[
                '1.0',  # facSysModel
                '2.0',  # facSysSerial
                '3.0',  # facSysVersion
                '201.1.0',  # facHaCurrentStatus
            ]),
    ],
)

register.check_plugin(
    name="fortiauthenticator_system",
    service_name="FortiAuthenticator System",
    discovery_function=discovery_fortiauthenticator_system,
    check_function=check_fortiauthenticator_system,
)
