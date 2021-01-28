#!/usr/bin/env python3
# author: Oguzhan Cicek, OpenSource Security GmbH - oguzhan(at)os-s.de

# Example Input:
# [...]
# .1.3.6.1.4.1.12356.118.3.1.1.0 v2.52-build0340 (GA)
# .1.3.6.1.4.1.12356.118.3.1.2.0 2
# .1.3.6.1.4.1.12356.118.3.1.3.0 4
# .1.3.6.1.4.1.12356.118.3.1.4.0 260459760
# .1.3.6.1.4.1.12356.118.3.1.5.0 710698
# .1.3.6.1.4.1.12356.118.3.1.6.0 3754417
# .1.3.6.1.4.1.12356.118.3.1.7.0 2
# .1.3.6.1.4.1.12356.118.3.1.8.0 32908349
# .1.3.6.1.4.1.12356.118.3.2.1.0 5.2.50534
# .1.3.6.1.4.1.12356.118.3.2.2.0 2.4.20034
# .1.3.6.1.4.1.12356.118.3.2.3.0 3.2.279
# .1.3.6.1.4.1.12356.118.3.2.4.0 4.478
# .1.3.6.1.4.1.12356.118.3.2.5.0 14.613
# [...]

# Example GUI Output:
# OK	FortiSandbox Memory	RAM used: 4.00% of 248 GiB

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


def parse_fortisandbox_mem(string_table: List[StringTable]) -> Section:
    return string_table[0][0]


def discovery_fortisandbox_mem(section: Section) -> DiscoveryResult:
    yield Service()


def check_fortisandbox_mem(params: Mapping[str, Tuple[float, float]],
                           section: Section) -> CheckResult:
    mem_usage_upper = params.get("mem_usage")
    memusage = float(section[0])
    memcap = 1024 * int(section[1])
    total = render.bytes(memcap)
    yield from check_levels(
        memusage,
        levels_upper=mem_usage_upper,
        metric_name="fortisandbox_memory_usage",
        label="RAM used",
        render_func=lambda v: "%.2f%% of %s" % (v, total),
    )


register.snmp_section(
    name="fortisandbox_mem",
    parse_function=parse_fortisandbox_mem,
    detect=equals('.1.3.6.1.2.1.1.2.0', '.1.3.6.1.4.1.12356.118.1.30006'),
    fetch=[
        SNMPTree(
            base='.1.3.6.1.4.1.12356.118.3.1',
            oids=[
                '3',  # fsaSysMemUsage
                '4',  # fsaSysMemCapacity
            ]),
    ],
)

register.check_plugin(
    name="fortisandbox_mem",
    service_name="FortiSandbox Memory",
    discovery_function=discovery_fortisandbox_mem,
    check_function=check_fortisandbox_mem,
    check_default_parameters={"mem_usage": (80.0, 90.0)},
    check_ruleset_name="fortisandbox_mem",
)
