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
# OK	FortiSandbox Memory	   RAM used: 4.00% - 9.94 GiB of 248 GiB

from .agent_based_api.v1.type_defs import (
    DiscoveryResult,
    CheckResult,
    StringTable,
)
from .utils.memory import (
    check_element,)
from .agent_based_api.v1 import (
    register,
    Service,
    equals,
    SNMPTree,
)
from typing import Mapping, Dict, List, Tuple

Section = Dict[str, float]


def parse_fortisandbox_mem(string_table: List[StringTable]) -> Section:
    mem_cap_kb = float(string_table[0][0][1])
    mem_cap = mem_cap_kb * 1024
    mem_used_perc = float(string_table[0][0][0])
    mem_used = (mem_cap / 100) * mem_used_perc
    parsed = {'memory_used': mem_used, 'memory_cap': mem_cap}
    return parsed


def discovery_fortisandbox_mem(section: Section) -> DiscoveryResult:
    yield Service()


def check_fortisandbox_mem(params: Mapping[str, Tuple[float, float]],
                           section: Section) -> CheckResult:
    warn, crit = params.get("levels", (0, 0))
    mem_used = section['memory_used']
    mem_cap = section['memory_cap']
    yield from check_element(
        'RAM used',
        mem_used,
        mem_cap,
        ("perc_used", (warn, crit)),
        create_percent_metric=True,
    )


register.snmp_section(
    name='fortisandbox_mem',
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
    name='fortisandbox_mem',
    service_name='FortiSandbox Memory',
    discovery_function=discovery_fortisandbox_mem,
    check_function=check_fortisandbox_mem,
    check_default_parameters={'levels': (80.0, 90.0)},
    check_ruleset_name='memory',
)
