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
# OK	FortiSandbox		Disk used: 5.28% used (694 GiB of 3.58 TiB)

from .agent_based_api.v1.type_defs import (
    DiscoveryResult,
    CheckResult,
    StringTable,
)
from .agent_based_api.v1 import (
    register,
    render,
    Service,
    equals,
    check_levels,
    SNMPTree,
)
from typing import Mapping, List, Tuple

Section = List[str]


def parse_fortisandbox_disk(string_table: List[StringTable]) -> Section:
    return string_table[0][0]


def discovery_fortisandbox_disk(section: Section) -> DiscoveryResult:
    yield Service()


def check_fortisandbox_disk(params: Mapping[str, Tuple[float, float]],
                            section: Section) -> CheckResult:
    disk_usage_upper = params.get("disk_usage")
    diskusage = 1024 * 1024 * float(section[0])
    diskcap = 1024 * 1024 * int(section[1])
    diskperc = float(diskcap / diskusage)
    display_diskusage = render.bytes(diskusage)
    display_diskcap = render.bytes(diskcap)
    yield from check_levels(
        diskperc,
        levels_upper=disk_usage_upper,
        metric_name="fortisandbox_disk_usage",
        label="Disk used",
        render_func=lambda v: "%.2f%% used (%s of %s)" % (v, display_diskusage, display_diskcap),
    )


register.snmp_section(
    name="fortisandbox_disk",
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
    name="fortisandbox_disk",
    service_name="FortiSandbox Disk usage",
    discovery_function=discovery_fortisandbox_disk,
    check_function=check_fortisandbox_disk,
    check_default_parameters={"disk_usage": (80.0, 90.0)},
    check_ruleset_name="fortisandbox_disk",
)
