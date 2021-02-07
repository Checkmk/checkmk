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
# OK	FortiSandbox Disk usage: total		18.93% used (694 GiB of 3.58 TiB),
#                                   trend per 1 day 0 hours: +0 B, trend per 1 day 0 hours: +0%

from .agent_based_api.v1.type_defs import (
    DiscoveryResult,
    CheckResult,
    StringTable,
)
from .utils.df import (
    df_check_filesystem_single,
    FILESYSTEM_DEFAULT_LEVELS,
)
from .agent_based_api.v1 import (
    register,
    Service,
    equals,
    SNMPTree,
    get_value_store,
)
from typing import Mapping, Dict, List, Tuple

Section = Dict[str, int]


def parse_fortisandbox_disk(string_table: List[StringTable]) -> Section:
    parsed = {'disk_used': int(string_table[0][0][0]), 'disk_cap': int(string_table[0][0][1])}
    return parsed


def discovery_fortisandbox_disk(section: Section) -> DiscoveryResult:
    yield Service(item="total")


def check_fortisandbox_disk(item: str, params: Mapping[str, Tuple[float, float]],
                            section: Section) -> CheckResult:
    disk_used = section['disk_used']
    disk_cap = section['disk_cap']
    disk_avail = disk_cap - disk_used
    yield from df_check_filesystem_single(
        value_store=get_value_store(),
        mountpoint=item,
        size_mb=disk_cap,
        avail_mb=disk_avail,
        reserved_mb=0,
        inodes_total=None,
        inodes_avail=None,
        params=params,
    )


register.snmp_section(
    name='fortisandbox_disk',
    parse_function=parse_fortisandbox_disk,
    detect=equals('.1.3.6.1.2.1.1.2.0', '.1.3.6.1.4.1.12356.118.1.30006'),
    fetch=[
        SNMPTree(
            base='.1.3.6.1.4.1.12356.118.3.1',
            oids=[
                '5',  # fsaSysDiskUsage
                '6',  # fsaSysDiskCapacity
            ]),
    ],
)

register.check_plugin(
    name='fortisandbox_disk',
    service_name='FortiSandbox Disk usage: %s',
    discovery_function=discovery_fortisandbox_disk,
    check_function=check_fortisandbox_disk,
    check_default_parameters=FILESYSTEM_DEFAULT_LEVELS,
    check_ruleset_name='filesystem',
)
