#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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

# failover off/ not configured
# [['Failover LAN Interface', '3', 'not Configured'],
#  ['Primary unit', '3', 'Failover Off'],
#  ['Secondary unit (this device)', '3', 'Failover Off']]

from dataclasses import dataclass
from typing import List, Mapping, Any

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


def get_cisco_asa_state_name(st: str) -> str:
    names = {
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
    return names.get(st, 'unknown %s' % st)


@dataclass
class Section:
    failover: bool
    local_role: str
    local_status: str
    local_status_detail: str
    failver_link_status: str
    remote_status: str


def parse_cisco_asa_failover(string_table: List[StringTable]) -> Section:
    failover = False
    for role, status, detail in string_table[0]:
        if 'this device' in role:
            if not 'failover off' in detail.lower():
                failover = True
            local_role = role.split(' ')[0].lower()
            local_status = status
            local_status_detail = detail
        elif 'failover' in role.lower():
            failver_link_status = status
        else:
            remote_status = status

    return Section(
        failover=failover,
        local_role=local_role,
        local_status=local_status,
        local_status_detail=local_status_detail,
        failver_link_status=failver_link_status,
        remote_status=remote_status
    )


def discovery_cisco_asa_failover(section: Section) -> DiscoveryResult:
    if section.failover:
        yield Service()


def check_cisco_asa_failover(params: (Mapping[str, Any]), section: Section) -> CheckResult:
    if isinstance(params, int):  # catch old params
        yield Result(state=State.CRIT, summary='This check is using old parameters. Please rescan (WATO) this device')
    else:
        yield Result(state=State.OK,
                     summary='Device (%s) is the %s' % (section.local_role, section.local_status_detail))

        if not params[section.local_role] == get_cisco_asa_state_name(section.local_status):
            yield Result(state=State(params['failover_state']),
                         summary='(The %s device should be %s)' % (section.local_role, params[section.local_role]))

        if not section.local_status in ['9', '10']:  # local not active/standby
            yield Result(state=State.WARN,
                         summary='Unhandled state %s reported' % get_cisco_asa_state_name(section.local_status))

        if not section.remote_status in ['9', '10']:  # remote not active/standby
            yield Result(state=State.WARN,
                         summary='Unhandled state %s for remote device reported' % get_cisco_asa_state_name(
                             section.remote_status))

        if not section.failver_link_status in ['2']:  # up
            yield Result(state=State.CRIT,
                         summary='Failover link state is %s' % get_cisco_asa_state_name(section.failver_link_status))


register.snmp_section(
    name='cisco_asa_failover',
    parse_function=parse_cisco_asa_failover,
    fetch=[
        SNMPTree(
            base='.1.3.6.1.4.1.9.9.147.1.2.1.1.1',  # CISCO-FIREWALL-MIB::cfwHardwareStatusEntry
            oids=[
                '2',  # CISCO-FIREWALL-MIB::cfwHardwareInformation
                '3',  # CISCO-FIREWALL-MIB::cfwHardwareStatusValue
                '4',  # CISCO-FIREWALL-MIB::cfwHardwareStatusDetail
            ]
        ),
    ],
    detect=any_of(
        startswith('.1.3.6.1.2.1.1.1.0', 'cisco adaptive security'),
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
