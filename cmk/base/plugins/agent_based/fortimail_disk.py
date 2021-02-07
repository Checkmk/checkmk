#!/usr/bin/env python3
# author: Oguzhan Cicek, OpenSource Security GmbH - oguzhan(at)os-s.de

#Example Input:
#[...]
#.1.3.6.1.4.1.12356.105.1.7.0 23
#.1.3.6.1.4.1.12356.105.1.8.0 0
#.1.3.6.1.4.1.12356.105.1.9.0 0
#.1.3.6.1.4.1.12356.105.1.10.0 2
#.1.3.6.1.4.1.12356.105.1.30.0 5
#[...]

#Example GUI Output:
#OK	FortiMail Disk usage		Disk usage: 0%

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


def parse_fortimail_disk(string_table: List[StringTable]) -> Section:
    parsed = {'disk_usage': float(string_table[0][0][0])}
    return parsed


def discovery_fortimail_disk(section: Section) -> DiscoveryResult:
    yield Service()


def check_fortimail_disk(params: Mapping[str, Tuple[float, float]],
                         section: Section) -> CheckResult:
    disk_usage_upper = params.get('mail_disk_usage')
    usage = section['disk_usage']
    yield from check_levels(
        usage,
        levels_upper=disk_usage_upper,
        metric_name='fortimail_disk_usage',
        label='Disk usage',
        render_func=lambda v: "%s%%" % v,
    )


register.snmp_section(
    name='fortimail_disk',
    parse_function=parse_fortimail_disk,
    detect=equals('.1.3.6.1.2.1.1.2.0', '.1.3.6.1.4.1.12356.105'),
    fetch=[
        SNMPTree(
            base='.1.3.6.1.4.1.12356.105.1',
            oids=[
                '9',  # fmlSysMailDiskUsage
            ]),
    ],
)

register.check_plugin(
    name='fortimail_disk',
    service_name='FortiMail disk usage',
    discovery_function=discovery_fortimail_disk,
    check_function=check_fortimail_disk,
    check_default_parameters={'mail_disk_usage': (80, 90)},
    check_ruleset_name='fortimail_disk',
)
