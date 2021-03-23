#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# License: GNU General Public License v2
#
# Author: thl-cmk[at]outlook[dot]com
# URL   : https://thl-cmk.hopto.org
# Date  : 2021-03-18
#
# rewrite of the original CMK2.0 check
#
#
# .1.3.6.1.4.1.9.9.147.1.2.1.1.1.2.4  'Failover LAN Interface'
# .1.3.6.1.4.1.9.9.147.1.2.1.1.1.2.6  'Primary unit (this device)'
# .1.3.6.1.4.1.9.9.147.1.2.1.1.1.2.7  'Secondary unit'
# .1.3.6.1.4.1.9.9.147.1.2.1.1.1.3.4  2
# .1.3.6.1.4.1.9.9.147.1.2.1.1.1.3.6  9     < These two values flip during
# .1.3.6.1.4.1.9.9.147.1.2.1.1.1.3.7  10    < failover
# .1.3.6.1.4.1.9.9.147.1.2.1.1.1.4.4  'LAN_FO GigabitEthernet0/0.777'
# .1.3.6.1.4.1.9.9.147.1.2.1.1.1.4.6  'Active unit'
# .1.3.6.1.4.1.9.9.147.1.2.1.1.1.4.7  'Standby unit'

# [['Failover LAN Interface', '2', 'LAN_FO GigabitEthernet0/0.777'],
#  ['Primary unit', '9', 'Active unit'],
#  ['Secondary unit (this device)', '10', 'Standby unit']]

from typing import Dict, List

from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import (
    DiscoveryResult,
    CheckResult,
    StringTable,
)

from cmk.base.plugins.agent_based.agent_based_api.v1 import (
    register,
    Service,
    Result,
    State,
    SNMPTree,
    startswith,
    contains,
    any_of,
)

#
# sample failover on
#
# [
#  [
#   ['Failover LAN Interface', '2', 'ClusterLink Port-channel4 (system)'],
#   ['Primary unit (this device)', '9', 'Active unit'],
#   ['Secondary unit', '10', 'Standby unit']
#  ]
# ]
#
# sample failover off --> _not configured_
# [
#  [
#   ['Failover LAN Interface', '3', 'not Configured'],
#   ['Primary unit', '3', 'Failover Off'],
#   ['Secondary unit (this device)', '3', 'Failover Off']
#  ]
# ]
#

cisco_asa_state_names = {
    '1': 'other',
    '2': 'up',
    '3': 'down',
    '4': 'error',
    '5': 'overTemp',
    '6': 'busy',
    '7': 'noMedia',
    '8': 'backup',
    '9': 'active',
    '10': 'standby',
}


def get_cmk_status(st: int) -> State:
    states = {
        0: State.OK,
        1: State.WARN,
        2: State.CRIT
    }
    return states.get(st, State.CRIT)


def parse_cisco_asa_failover(string_table: List[StringTable]) -> Dict:
    def parse_line(line):
        role = line[0].split(' ')[0].lower()
        data = [role, line[1], line[2].lower()]
        return data

    parsed = {}
    for line in string_table[0]:
        if 'this device' in line[0].lower():
            if line[2].lower() == 'failover off':
                return None
            parsed['local'] = parse_line(line)
        elif 'failover' in line[0].lower():
            parsed['failover'] = line
        else:
            parsed['remote'] = parse_line(line)
    return parsed


#
# {'failover': ['Failover LAN Interface', '2', 'ClusterLink Port-channel4 (system)'],
#  'local': ['primary', '9', 'active unit'],
#  'remote': ['secondary', '10', 'standby unit']}
#
def discovery_cisco_asa_failover(section: Dict) -> DiscoveryResult:
    yield Service()


def _convert_params(params):
    if isinstance(params, int):
        # Very old case: primary state was remembered during discovery
        # and stored as an integer: return [(None, int(info[1][1]))]
        return {
            'primary': cisco_asa_state_names['%s' % params],
            'secondary': 'standby',
            'failover_state': 1,
        }
    return params


def check_cisco_asa_failover(params, section: Dict) -> CheckResult:
    converted_params = _convert_params(params)

    role = section['local'][0]
    status = section['local'][1]
    status_readable = cisco_asa_state_names[status]
    status_detail = section['local'][2]

    yield Result(state=State.OK, summary='Device (%s) is the %s' % (role, status_detail))

    p_role = converted_params[role]
    if not p_role == status_readable:
        yield Result(state=get_cmk_status(converted_params['failover_state']),
                     summary='(The %s device should be %s)' % (role, p_role))

    if not status in ['9', '10']:
        yield Result(state=State.WARN, summary='Unhandled state %s reported' % status_readable)


register.snmp_section(
    name='cisco_asa_failover',
    parse_function=parse_cisco_asa_failover,
    fetch=[
        SNMPTree(
            base='.1.3.6.1.4.1.9.9.147.1.2.1.1.1',  #
            oids=[
                '2',  # CISCO-FIREWALL-MIB::cfwHardwareInformation
                '3',  # CISCO-FIREWALL-MIB::cfwHardwareStatusValue
                '4',  # CISCO-FIREWALL-MIB::cfwHardwareStatusDetail
            ]
        ),
    ],
    detect=any_of(
        startswith('.1.3.6.1.2.1.1.1.0', 'cisco adaptive security'),
        startswith('.1.3.6.1.2.1.1.1.0', 'cisco firepower threat defense'),
        contains('.1.3.6.1.2.1.1.1.0', 'cisco pix security'),

    )
)

register.check_plugin(
    name='cisco_asa_failover',
    service_name='Cluster Status',
    discovery_function=discovery_cisco_asa_failover,
    check_function=check_cisco_asa_failover,
    check_default_parameters={'primary': 'active',
                              'secondary': 'standby',
                              'failover_state': 1,
                              },
    check_ruleset_name='cisco_asa_failover'
)
