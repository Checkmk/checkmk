#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from cmk.agent_based.v2 import (
    exists,
    InventoryPlugin,
    InventoryResult,
    OIDBytes,
    SNMPSection,
    SNMPTree,
    StringByteTable,
)
from cmk.plugins.lib import uptime
from cmk.plugins.lib.interfaces import render_mac_address
from cmk.plugins.lib.inventory_interfaces import Interface, inventorize_interfaces, InventoryParams


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


def _process_sub_table(sub_table: Sequence[str | Sequence[int]]) -> Iterable[Interface]:
    """
    >>> from pprint import pprint
    >>> pprint(list(_process_sub_table(['49160', 'gigabitEthernet 1/0/8', 'pve-muc1-ipmi', '6',
    ... '1000000000', '1000', '1', '1', [116, 218, 136, 88, 22, 17], '761116702'])))
    [Interface(index='49160',
               descr='gigabitEthernet 1/0/8',
               alias='pve-muc1-ipmi',
               type='6',
               speed=1000000000,
               oper_status=1,
               phys_address='74:DA:88:58:16:11',
               admin_status=1,
               last_change=7611167.02,
               bond=None)]
    >>> pprint(list(_process_sub_table(['49160', 'gigabitEthernet 1/0/8', 'pve-muc1-ipmi', '231',
    ... '1000000000', '1000', '1', '1', [116, 218, 136, 88, 22, 17], '761116702'])))
    []
    >>> pprint(list(_process_sub_table(['49160', 'gigabitEthernet 1/0/8', 'pve-muc1-ipmi', '6',
    ... '', '1000', '1', '1', [116, 218, 136, 88, 22, 17], '761116702'])))
    []
    >>> pprint(list(_process_sub_table(['49160', 'gigabitEthernet 1/0/8', 'pve-muc1-ipmi', '6',
    ... '1000000000', '1000', '1', '1', [116, 218, 136, 88, 22, 17], ''])))
    []
    >>> pprint(list(_process_sub_table(["NULL", "NULL", "", "NULL", "NULL", "", "NULL", "NULL",
    ... [78, 85, 76, 76], "NULL"]))) # innovaphone IP811
    []
    """
    index, descr, alias, type_, speed, high_speed, oper_status, admin_status = (
        str(x) for x in sub_table[:-2]
    )
    last_change = str(sub_table[-1])

    # Ignore useless entries for "TenGigabitEthernet2/1/21--Uncontrolled" (type) or half-empty
    # tables (e.g. Viprinet-Router)
    if type_ in ("231", "232") or last_change in ("", "NULL") or not speed:
        return

    yield Interface(
        index=index,
        descr=descr,
        alias=alias,
        type=type_,
        speed=int(high_speed) * 1000 * 1000 if high_speed else int(speed),
        oper_status=int(oper_status) if oper_status.isdigit() else None,
        phys_address=render_mac_address(sub_table[-2]),
        admin_status=int(admin_status) if admin_status else None,
        last_change=_process_last_change(last_change),
    )


def parse_inv_if(string_table: Sequence[StringByteTable]) -> SectionInvIf:
    return SectionInvIf(
        [
            iface_and_last_change
            for interface_data in string_table[0]
            for iface_and_last_change in _process_sub_table(interface_data)
        ],
        len(string_table[0]),
    )


snmp_section_inv_if = SNMPSection(
    name="inv_if",
    parse_function=parse_inv_if,
    fetch=[
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
    detect=exists(".1.3.6.1.2.1.2.2.1.*"),  # ifTable
)


def inventory_if(
    params: InventoryParams,
    section_inv_if: SectionInvIf | None,
    section_uptime: uptime.Section | None,
) -> InventoryResult:
    if section_inv_if is None or section_uptime is None or section_uptime.uptime_sec is None:
        return
    yield from inventorize_interfaces(
        params,
        section_inv_if.interfaces,
        section_inv_if.n_interfaces_total,
        uptime_sec=section_uptime.uptime_sec,
    )


inventory_plugin_inv_if = InventoryPlugin(
    name="inv_if",
    inventory_function=inventory_if,
    inventory_default_parameters={},
    inventory_ruleset_name="inv_if",
    sections=["inv_if", "uptime"],
)
