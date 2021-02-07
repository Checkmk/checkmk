#!/usr/bin/env python3
# author: Oguzhan Cicek, OpenSource Security GmbH - oguzhan(at)os-s.de

#Example Input:
#[...]
#.1.3.6.1.4.1.12356.105.1.9.0 0
#.1.3.6.1.4.1.12356.105.1.10.0 2
#.1.3.6.1.4.1.12356.105.1.30.0 5
#.1.3.6.1.4.1.12356.105.1.101.1.0 15
#.1.3.6.1.4.1.12356.105.1.101.2.0 0
#[...]

#Example GUI Output:
#OK FortiMail System load       System load: 5%

from .agent_based_api.v1.type_defs import (
    DiscoveryResult,
    CheckResult,
    StringTable,
)
from .agent_based_api.v1 import (
    register,
    Service,
    equals,
    check_levels,
    SNMPTree,
)
from typing import Mapping, Dict, List, Tuple

Section = Dict[str, float]


def parse_fortimail_sysload(string_table: List[StringTable]) -> Section:
    parsed = {'sysload': float(string_table[0][0][0])}
    return parsed


def discovery_fortimail_sysload(section: Section) -> DiscoveryResult:
    yield Service()


def check_fortimail_sysload(params: Mapping[str, Tuple[float, float]],
                            section: Section) -> CheckResult:
    mail_sysload_upper = params.get('mail_sysload')
    sysload = section['sysload']
    yield from check_levels(
        sysload,
        levels_upper=mail_sysload_upper,
        metric_name='fortimail_system_load',
        label='System load',
        render_func=lambda v: "%s%%" % v,
    )


register.snmp_section(
    name='fortimail_sysload',
    parse_function=parse_fortimail_sysload,
    detect=equals('.1.3.6.1.2.1.1.2.0', '.1.3.6.1.4.1.12356.105'),
    fetch=[
        SNMPTree(
            base='.1.3.6.1.4.1.12356.105.1',
            oids=[
                '30',  # fmlSysLoad
            ]),
    ],
)

register.check_plugin(
    name='fortimail_sysload',
    service_name='FortiMail system load',
    discovery_function=discovery_fortimail_sysload,
    check_function=check_fortimail_sysload,
    check_default_parameters={'mail_sysload': (90, 95)},
    check_ruleset_name='fortimail_sysload',
)
