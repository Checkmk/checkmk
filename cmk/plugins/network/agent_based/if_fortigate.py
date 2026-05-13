#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time

from cmk.agent_based.v1.type_defs import StringByteTable
from cmk.agent_based.v2 import SimpleSNMPSection, SNMPTree, startswith
from cmk.plugins.lib import if64, interfaces


def parse_if_fortigate(
    string_table: StringByteTable,
) -> interfaces.Section[interfaces.InterfaceWithCounters]:
    return if64.parse_if64(string_table, time.time())


# Real ifAlias (slot 18) is restored to its proper place — `if64` itself now fetches
# ifName at slot 21 and routes it to the `name` attribute. History: werks 4539 -> 6638
# -> 11267 previously exposed ifName as ifAlias because `name` did not exist yet.
END_OIDS = if64.END_OIDS + ["2.2.1.7"]  # ifAdminStatus appended

snmp_section_if_fortigate = SimpleSNMPSection(
    name="if_fortigate",
    parse_function=parse_if_fortigate,
    parsed_section_name="interfaces",
    fetch=SNMPTree(
        base=if64.BASE_OID,
        oids=END_OIDS,
    ),
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.12356"),
    supersedes=["if", "if64"],
)
