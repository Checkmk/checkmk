#!/usr/bin/env python3
# author: Oguzhan Cicek, OpenSource Security GmbH - oguzhan(at)os-s.de

#Example Input:
#[...]
#.1.3.6.1.4.1.12356.105.1.102.2.1.9.1 540
#.1.3.6.1.4.1.12356.105.1.102.2.1.9.2 0
#.1.3.6.1.4.1.12356.105.1.103.1.0 0
#.1.3.6.1.4.1.12356.105.1.103.2.1.1.1 1
#.1.3.6.1.4.1.12356.105.1.103.2.1.1.2 2
#.1.3.6.1.4.1.12356.105.1.103.2.1.1.3 3
#.1.3.6.1.4.1.12356.105.1.103.2.1.1.4 4
#.1.3.6.1.4.1.12356.105.1.103.2.1.1.5 5
#.1.3.6.1.4.1.12356.105.1.103.2.1.1.6 6
#.1.3.6.1.4.1.12356.105.1.103.2.1.2.1 default queue
#.1.3.6.1.4.1.12356.105.1.103.2.1.2.2 default slow queue
#.1.3.6.1.4.1.12356.105.1.103.2.1.2.3 incoming queue
#.1.3.6.1.4.1.12356.105.1.103.2.1.2.4 incoming slow queue
#.1.3.6.1.4.1.12356.105.1.103.2.1.2.5 outgoing queue
#.1.3.6.1.4.1.12356.105.1.103.2.1.2.6 outgoing slow queue
#.1.3.6.1.4.1.12356.105.1.103.2.1.3.1 0
#.1.3.6.1.4.1.12356.105.1.103.2.1.3.2 31
#.1.3.6.1.4.1.12356.105.1.103.2.1.3.3 0
#.1.3.6.1.4.1.12356.105.1.103.2.1.3.4 0
#.1.3.6.1.4.1.12356.105.1.103.2.1.3.5 0
#.1.3.6.1.4.1.12356.105.1.103.2.1.3.6 0
#.1.3.6.1.4.1.12356.105.1.103.2.1.4.1 0
#.1.3.6.1.4.1.12356.105.1.103.2.1.4.2 534
#.1.3.6.1.4.1.12356.105.1.103.2.1.4.3 0
#.1.3.6.1.4.1.12356.105.1.103.2.1.4.4 0
#.1.3.6.1.4.1.12356.105.1.103.2.1.4.5 0
#.1.3.6.1.4.1.12356.105.1.103.2.1.4.6 0
#.1.3.6.1.4.1.12356.105.1.110.1.0 2
#.1.3.6.1.4.1.12356.105.1.110.2.1.1.1 1
#[...]

#Example GUI Output:
#OK	FortiMail default queue			Mail count 0 - Mail size 0 B
#OK	FortiMail default slow queue	Mail count 31 - Mail size 534 KiB
#OK	FortiMail incoming queue		Mail count 0 - Mail size 0 B
#OK	FortiMail incoming slow queue	Mail count 0 - Mail size 0 B
#OK	FortiMail outgoing queue		Mail count 0 - Mail size 0 B
#OK	FortiMail outgoing slow queue	Mail count 0 - Mail size 0 B

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
from typing import Mapping, List, Tuple, Dict

Section = Dict[str, Dict[str, int]]


def parse_fortimail_queue(string_table: List[StringTable]) -> Section:
    parsed = {}
    for i in range(len(string_table[0])):
        mail_count = int(string_table[0][i][1])
        mail_size = int(string_table[0][i][2]) * 1024
        parsed.update({string_table[0][i][0]: {'mail_count': mail_count, 'mail_size': mail_size}})
    return parsed


def discovery_fortimail_queue(section: Section) -> DiscoveryResult:
    for key in section:
        yield Service(item=key)


def check_fortimail_queue(item: str, params: Mapping[str, Tuple[float, float]],
                          section: Section) -> CheckResult:
    queued_mails_upper = params.get('queued_mails')
    mail_count = section[item]['mail_count']
    mail_size = section[item]['mail_size']
    yield from check_levels(
        mail_count,
        levels_upper=queued_mails_upper,
        metric_name='fortimail_queue_count',
        label='',
        render_func=lambda v, s=mail_size: "Mail count %s - Mail size %s" % (v, render.bytes(s)),
    )


register.snmp_section(
    name='fortimail_queue',
    parse_function=parse_fortimail_queue,
    detect=equals('.1.3.6.1.2.1.1.2.0', '.1.3.6.1.4.1.12356.105'),
    fetch=[
        SNMPTree(
            base='.1.3.6.1.4.1.12356.105.1.103.2.1',
            oids=[
                '2',  # fmlMailQueueName
                '3',  # fmlMailQueueMailCount
                '4',  # fmlMailQueueMailSize
            ]),
    ],
)

register.check_plugin(
    name='fortimail_queue',
    service_name='FortiMail %s',
    discovery_function=discovery_fortimail_queue,
    check_function=check_fortimail_queue,
    check_default_parameters={'queued_mails': (100, 200)},
    check_ruleset_name='fortimail_queue',
)
