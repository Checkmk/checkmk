#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# License: GNU General Public License v2
#
# Author: thl-cmk[at]outlook[dot]com
# URL   : https://thl-cmk.hopto.org
# Date  : 2020-11-26
#
# add interface name to inventory
#
# 2021-07-01: cleanup, rename snmp_section from ifname to inv_ifname
# 2023-06-03: moved gui files to ~/local/lib/chek_mk/gui/plugins/...
# 2023-06-15: added key_columns: desc and alias to match CMK 2.2.x
# 2023-09-01: fix parse function if both interface tables don't match (THX to joerg[dot]ott[at]outlook[dot]com)
# 2024-04-19: refactoring for CMK2.3.0b5 (removed description/alias), only if_index is key column now again.
# 2024-07-22: detect function changed to check if IF-MIB::ifXTable.ifName exists
# 2025-03-23: modified for CMK 2.4.0x
# 2025-04-03: fixed wrong snmp_section/inventory_plugin identifier
#             changed string_table to list, why? SNMPSection -> SimpleSNMPSection
#   File "/omd/sites/build/lib/python3/cmk/base/api/agent_based/register/section_plugins.py", line 184, in _validate_type_list_snmp_trees
#     raise TypeError("value of 'fetch' keyword must be SNMPTree or non-empty list of SNMPTrees")
# 2025-11-12: SNMPSection -> SimpleSNMPSection

# sample snmpwalk
# .1.3.6.1.2.1.31.1.1.1.1.1 = STRING: lo
# .1.3.6.1.2.1.31.1.1.1.1.2 = STRING: eth-idrc0
# .1.3.6.1.2.1.31.1.1.1.1.3 = STRING: eth1
# .1.3.6.1.2.1.31.1.1.1.1.4 = STRING: eth2
# .1.3.6.1.2.1.31.1.1.1.1.5 = STRING: eth3
# .1.3.6.1.2.1.31.1.1.1.1.6 = STRING: Mgmt
# .1.3.6.1.2.1.31.1.1.1.1.7 = STRING: bond1
# .1.3.6.1.2.1.31.1.1.1.1.8 = STRING: bond1.3000
# .1.3.6.1.2.1.31.1.1.1.1.9 = STRING: bond1.3001
#

from typing import Mapping, Sequence
from cmk.agent_based.v2 import (
    InventoryPlugin,
    InventoryResult,
    OIDEnd,
    SNMPTree,
    SimpleSNMPSection,
    StringTable,
    TableRow,
    exists,
)


def parse_inv_if_name(string_table: StringTable) -> Mapping[int, str] | None:
    try:
        return {int(if_index): if_name for if_index, if_name in string_table if if_name and if_index.isdigit()}
    except IndexError:
        return None


def inventory_inv_if_name(section: Mapping[int, str]) -> InventoryResult:
    path = ['networking', 'interfaces']
    for if_index, if_name in section.items():
        yield TableRow(
            path=path,
            key_columns={
                "index": if_index,
            },
            inventory_columns={
                'name': if_name
            },
        )


snmp_section_inv_if_name = SimpleSNMPSection(
    name='inv_if_name',
    parse_function=parse_inv_if_name,
    fetch=SNMPTree(
        base='.1.3.6.1.2.1.31.1.1.1',  # IF-MIB::ifXTable
        oids=[
            OIDEnd(),  # ifIndex
            '1',  # ifName
        ]),
    detect=exists('.1.3.6.1.2.1.31.1.1.1.1.*')
)

inventory_plugin_if_name = InventoryPlugin(
    name='inv_if_name',
    inventory_function=inventory_inv_if_name,
)
