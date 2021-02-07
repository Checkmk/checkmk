#!/usr/bin/env python3
# author: Oguzhan Cicek, OpenSource Security GmbH - oguzhan(at)os-s.de

#Example Input:
#.1.3.6.1.2.1.1.1.0 test
#.1.3.6.1.2.1.1.2.0 .1.3.6.1.4.1.12356.101.1.15000
#[...]
#.1.3.6.1.4.1.12356.101.8.2.1.1.1.102 0
#.1.3.6.1.4.1.12356.101.8.2.1.1.1.103 0
#.1.3.6.1.4.1.12356.101.8.2.1.1.1.104 0
#.1.3.6.1.4.1.12356.101.8.2.1.1.1.105 0
#.1.3.6.1.4.1.12356.101.8.2.1.1.1.106 0
#.1.3.6.1.4.1.12356.101.8.2.1.1.2.102 0
#.1.3.6.1.4.1.12356.101.8.2.1.1.2.103 0
#.1.3.6.1.4.1.12356.101.8.2.1.1.2.104 0
#.1.3.6.1.4.1.12356.101.8.2.1.1.2.105 0
#.1.3.6.1.4.1.12356.101.8.2.1.1.2.106 0
#[...]

#Example GUI Output:
#OK	FortiGate AntiVirus Info: 0
#       Viruses per second: detected: 0.00, blocked: 0.00
#OK	FortiGate AntiVirus Info: 1
#       Viruses per second: detected: 0.00, blocked: 0.00
#OK	FortiGate AntiVirus Info: 2
#       Viruses per second: detected: 0.00, blocked: 0.00
#OK	FortiGate AntiVirus Info: 3
#       Viruses per second: detected: 0.00, blocked: 0.00
#OK	FortiGate AntiVirus Info: 4
#       Viruses per second: detected: 0.00, blocked: 0.00

from .agent_based_api.v1.type_defs import (
    DiscoveryResult,
    CheckResult,
    StringTable,
)
from .agent_based_api.v1 import (
    register,
    get_rate,
    Service,
    startswith,
    Metric,
    SNMPTree,
    check_levels,
    get_value_store,
)
from typing import List, Dict, Mapping, Tuple
import time

Section = Dict[str, Dict[str, int]]


def parse_fortigate_antivirus(string_table: List[StringTable]) -> Section:
    parsed = {}
    for i in range(len(string_table[0])):
        parsed.update({
            str(i): {
                'detected': int(string_table[0][i][0]),
                'blocked': int(string_table[0][i][1])
            }
        })
    return parsed


def discovery_fortigate_antivirus(section: Section) -> DiscoveryResult:
    for key in section:
        yield Service(item=key)


def check_fortigate_antivirus(item: str, params: Mapping[str, Tuple[float, float]],
                              section: Section) -> CheckResult:
    detected_levels = params.get('detections')
    detected = section[item]['detected']
    blocked = section[item]['blocked']
    value_store = get_value_store()
    now = time.time()
    detected_rate = get_rate(value_store, ('detected_rate_%s' % (item)), now, detected)
    blocked_rate = get_rate(value_store, ('blocked_rate_%s' % (item)), now, blocked)
    yield from check_levels(detected_rate,
                            levels_upper=detected_levels,
                            metric_name='fortigate_antivirus_detected_sec',
                            label='Viruses per second',
                            render_func=lambda v: 'detected: %.2f, blocked: %.2f ' %
                            (detected_rate, blocked_rate))
    yield Metric('fortigate_antivirus_blocked_sec', blocked_rate)


register.snmp_section(
    name='fortigate_antivirus',
    parse_function=parse_fortigate_antivirus,
    detect=startswith('.1.3.6.1.2.1.1.2.0', '.1.3.6.1.4.1.12356.101.1.'),
    fetch=[
        SNMPTree(
            base='.1.3.6.1.4.1.12356.101.8.2.1.1',
            oids=[
                '1',  # fgAvVirusDetected
                '2',  # fgAvVirusBlocked
            ]),
    ],
)

register.check_plugin(
    name='fortigate_antivirus',
    service_name='FortiGate AntiVirus Info: %s',
    discovery_function=discovery_fortigate_antivirus,
    check_function=check_fortigate_antivirus,
    check_ruleset_name='fortigate_antivirus',
    check_default_parameters={'detections': (100, 300)},
)
