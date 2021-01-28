#!/usr/bin/env python3
# author: Oguzhan Cicek, OpenSource Security GmbH - oguzhan(at)os-s.de

#Example Input:
#.1.3.6.1.2.1.1.1.0 testname
#.1.3.6.1.2.1.1.2.0 .1.3.6.1.4.1.12356.101.1.15000
#[...]
#.1.3.6.1.4.1.12356.101.9.2.1.1.1.102 1
#.1.3.6.1.4.1.12356.101.9.2.1.1.1.103 2
#.1.3.6.1.4.1.12356.101.9.2.1.1.1.104 3
#.1.3.6.1.4.1.12356.101.9.2.1.1.1.105 4
#.1.3.6.1.4.1.12356.101.9.2.1.1.1.106 5
#.1.3.6.1.4.1.12356.101.9.2.1.1.2.102 11
#.1.3.6.1.4.1.12356.101.9.2.1.1.2.103 22
#.1.3.6.1.4.1.12356.101.9.2.1.1.2.104 33
#.1.3.6.1.4.1.12356.101.9.2.1.1.2.105 44
#.1.3.6.1.4.1.12356.101.9.2.1.1.2.106 55
#[...]

#Example GUI Output:
#OK     FortiGate IPS Info: 0
#       Average amount of Intrusions in last 5 Min.: detected: 0.00, blocked: 0.00
#OK     FortiGate IPS Info: 1
#       Average amount of Intrusions in last 5 Min.: detected: 0.00, blocked: 0.00
#OK     FortiGate IPS Info: 2
#       Average amount of Intrusions in last 5 Min.: detected: 0.00, blocked: 0.00
#OK	FortiGate IPS Info: 3
#       Average amount of Intrusions in last 5 Min.: detected: 0.00, blocked: 0.00
#OK     FortiGate IPS Info: 4
#       Average amount of Intrusions in last 5 Min.: detected: 0.00, blocked: 0.00

from .agent_based_api.v1.type_defs import (
    DiscoveryResult,
    CheckResult,
    StringTable,
)
from .agent_based_api.v1 import (
    register,
    get_average,
    Service,
    startswith,
    Metric,
    SNMPTree,
    check_levels,
    get_value_store,
)
from typing import List, Mapping, Tuple
import time

Section = List[List[str]]


def parse_fortigate_ips(string_table: List[StringTable]) -> Section:
    return string_table[0]


def discovery_fortigate_ips(section: Section) -> DiscoveryResult:
    for pos in range(0, len(section)):
        yield Service(item=str(pos))


def check_fortigate_ips(item: str, params: Mapping[str, Tuple[float, float]],
                        section: Section) -> CheckResult:
    detected_levels = params.get("intrusions")
    detected = int(section[int(item)][0])
    blocked = int(section[int(item)][1])
    value_store = get_value_store()
    now = time.time()
    detected_rate = get_average(value_store, ("detected_rate_%s" % (item)), now, detected, 5)
    blocked_rate = get_average(value_store, ("blocked_rate_%s" % (item)), now, blocked, 5)
    yield from check_levels(detected_rate,
                            levels_upper=detected_levels,
                            metric_name="fortigate_ips_detected_5min",
                            label="Average amount of Intrusions in last 5 Min.",
                            render_func=lambda v: "detected: %.2f, blocked: %.2f " %
                            (detected_rate, blocked_rate))
    yield Metric("fortigate_ips_blocked_5min", blocked_rate)


register.snmp_section(
    name="fortigate_ips",
    parse_function=parse_fortigate_ips,
    detect=startswith('.1.3.6.1.2.1.1.2.0', '.1.3.6.1.4.1.12356.101.1.'),
    fetch=[
        SNMPTree(
            base='.1.3.6.1.4.1.12356.101.9.2.1.1',
            oids=[
                '1',  # fgIpsIntrusionsDetected
                '2',  # fgIpsIntrusionsBlocked
            ]),
    ],
)

register.check_plugin(
    name="fortigate_ips",
    service_name="FortiGate IPS Info: %s",
    discovery_function=discovery_fortigate_ips,
    check_function=check_fortigate_ips,
    check_ruleset_name="fortigate_ips",
    check_default_parameters={"intrusions": (100, 300)},
)
