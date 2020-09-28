#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
import time
from typing import Iterable, Optional, Sequence, Union

from .agent_based_api.v1.type_defs import InventoryResult, Parameters, SNMPStringByteTable
from .agent_based_api.v1 import (
    Attributes,
    matches,
    OIDBytes,
    register,
    SNMPTree,
    TableRow,
)
from .utils.interfaces import render_mac_address


@dataclass
class Interface:
    index: str
    descr: str
    alias: str
    type: str
    speed: int
    oper_status: int
    phys_address: str
    admin_status: int
    last_change: float


@dataclass
class SectionInvIf:
    interfaces: Sequence[Interface]
    n_interfaces_total: int


def _process_last_change(last_change_str: str) -> float:
    """
    >>> _process_last_change('123456')
    1234.56
    >>> _process_last_change('0:0:01:09.92')
    69.92
    """
    # last_change_str can be of type Timeticks (100th of seconds) or a human readable time stamp
    # (yurks)
    try:
        return float(last_change_str) / 100.0
    except ValueError:
        # Example: 0:0:01:09.96
        parts = last_change_str.split(":")
        days = int(parts[0])
        hours = int(parts[1])
        minutes = int(parts[2])
        seconds = float(parts[3])
        return seconds + 60 * minutes + 3600 * hours + 86400 * days


def _process_sub_table(sub_table: Sequence[Union[str, Sequence[int]]]) -> Iterable[Interface]:
    """
    >>> from pprint import pprint
    >>> pprint(list(_process_sub_table(['49160', 'gigabitEthernet 1/0/8', 'pve-muc1-ipmi', '6',
    ... '1000000000', '1000', '1', '1', [116, 218, 136, 88, 22, 17], '761116702'])))
    [Interface(index='49160', descr='gigabitEthernet 1/0/8', alias='pve-muc1-ipmi', type='6', speed=1000000000, oper_status=1, phys_address='74:DA:88:58:16:11', admin_status=1, last_change=7611167.02)]
    >>> pprint(list(_process_sub_table(['49160', 'gigabitEthernet 1/0/8', 'pve-muc1-ipmi', '231',
    ... '1000000000', '1000', '1', '1', [116, 218, 136, 88, 22, 17], '761116702'])))
    []
    >>> pprint(list(_process_sub_table(['49160', 'gigabitEthernet 1/0/8', 'pve-muc1-ipmi', '6',
    ... '', '1000', '1', '1', [116, 218, 136, 88, 22, 17], '761116702'])))
    []
    >>> pprint(list(_process_sub_table(['49160', 'gigabitEthernet 1/0/8', 'pve-muc1-ipmi', '6',
    ... '1000000000', '1000', '1', '1', [116, 218, 136, 88, 22, 17], ''])))
    []
    """
    index, descr, alias, type_, speed, high_speed, oper_status, admin_status = (
        str(x) for x in sub_table[:-2])
    last_change = str(sub_table[-1])

    # Ignore useless entries for "TenGigabitEthernet2/1/21--Uncontrolled" (type) or half-empty
    # tables (e.g. Viprinet-Router)
    if type_ in ("231", "232") or not last_change or not speed:
        return

    yield Interface(
        index=index,
        descr=descr,
        alias=alias,
        type=type_,
        speed=int(high_speed) * 1000 * 1000 if high_speed else int(speed),
        oper_status=int(oper_status),
        phys_address=render_mac_address(sub_table[-2]),
        admin_status=int(admin_status),
        last_change=_process_last_change(last_change),
    )


def parse_inv_if(string_table: SNMPStringByteTable) -> SectionInvIf:
    return SectionInvIf(
        [
            iface_and_last_change for interface_data in string_table[0]
            for iface_and_last_change in _process_sub_table(interface_data)
        ],
        len(string_table[0]),
    )


register.snmp_section(
    name="inv_if",
    parse_function=parse_inv_if,
    trees=[
        SNMPTree(
            base=".1.3.6.1.2.1",
            oids=[
                "2.2.1.1",  # ifIndex
                "2.2.1.2",  # ifDescr
                "31.1.1.1.18",  # ifAlias
                "2.2.1.3",  # ifType
                "2.2.1.5",  # ifSpeed
                "31.1.1.1.15",  # ifHighSpeed   .. 1000 means 1Gbit
                "2.2.1.8",  # ifOperStatus
                "2.2.1.7",  # ifAdminStatus
                OIDBytes("2.2.1.6"),  # ifPhysAddress
                "2.2.1.9",  # ifLastChange
            ],
        ),
    ],
    # match all cont/version strings >= 2
    detect=matches(".1.3.6.1.2.1.2.1.0", r"([2-9]|\d\d+)(\.\d*)*"),
)


def round_to_day(ts):
    broken = time.localtime(ts)
    return time.mktime((broken.tm_year, broken.tm_mon, broken.tm_mday, 0, 0, 0, broken.tm_wday,
                        broken.tm_yday, broken.tm_isdst))


# TODO unify with other if inventory plugins
def inventory_if(
    params: Parameters,
    section_inv_if: Optional[SectionInvIf],
    section_snmp_uptime: Optional[int],
) -> InventoryResult:
    if section_inv_if is None or section_snmp_uptime is None:
        return

    now = time.time()

    usage_port_types = params.get(
        "usage_port_types",
        ['6', '32', '62', '117', '127', '128', '129', '180', '181', '182', '205', '229'])
    unused_duration = params.get("unused_duration", 30 * 86400)

    total_ethernet_ports = 0
    available_ethernet_ports = 0

    for interface in section_inv_if.interfaces:

        if interface.last_change > 0:
            state_age = section_snmp_uptime - interface.last_change

            # Assume counter rollover in case uptime is less than last_change and
            # add 497 days (counter maximum).
            # This way no negative change times are shown anymore. The state change is shown
            # wrong in case it's really 497 days ago when state changed but there's no way to
            # get the count of rollovers since change (or since uptime) and it's better the
            # wrong negative state change is not shown anymore...
            if state_age < 0:
                state_age = 42949672 - interface.last_change + section_snmp_uptime

        else:
            # Assume point of time of boot as last state change.
            state_age = section_snmp_uptime

        last_change_timestamp = round_to_day(now - state_age)

        # in case ifIndex is missing
        try:
            if_index_nr: Union[str, int] = int(interface.index)
        except ValueError:
            if_index_nr = ""

        interface_row = {
            "speed": interface.speed,
            "phys_address": interface.phys_address,
            "oper_status": interface.oper_status,
            "admin_status": interface.admin_status,  # 1(up) or 2(down)
            "port_type": int(interface.type),
        }

        if interface.type in usage_port_types:
            total_ethernet_ports += 1
            if_available = interface.oper_status == 2 and state_age > unused_duration
            if if_available:
                available_ethernet_ports += 1
            interface_row["available"] = if_available

        yield TableRow(path=["networking", "interfaces"],
                       key_columns={"index": if_index_nr},
                       inventory_columns=interface_row,
                       status_columns={
                           "description": interface.descr,
                           "alias": interface.alias,
                           "last_change": int(last_change_timestamp),
                       })

    yield Attributes(
        path=["networking"],
        inventory_attributes={
            "available_ethernet_ports": str(available_ethernet_ports),
            "total_ethernet_ports": str(total_ethernet_ports),
            "total_interfaces": str(section_inv_if.n_interfaces_total),
        },
    )


register.inventory_plugin(
    name='inv_if',
    inventory_function=inventory_if,
    inventory_default_parameters={},
    inventory_ruleset_name="inv_if",
    sections=["inv_if", "snmp_uptime"],
)
