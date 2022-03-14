#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from .agent_based_api.v1 import all_of, contains, OIDBytes, register, SNMPTree, type_defs
from .utils import if64, interfaces


def parse_if64_tplink(string_table: type_defs.StringByteTable) -> interfaces.Section:
    preprocessed_lines = []
    for line in string_table:
        # if we have no special alias info we use the standard ifAlias info
        if not line[18]:
            line[18] = line[20]
        line[3] = if64.fix_if_64_highspeed(str(line[3]))
        # cut away the last column with the optional ifAlias info
        preprocessed_lines.append(line[:20])
    return if64.generic_parse_if64(preprocessed_lines)


register.snmp_section(
    name="if64_tplink",
    parse_function=parse_if64_tplink,
    parsed_section_name="interfaces",
    fetch=SNMPTree(
        base=".1.3.6.1",
        oids=[
            "2.1.2.2.1.1",  # ifIndex                    0
            "2.1.2.2.1.2",  # ifDescr                    1
            "2.1.2.2.1.3",  # ifType                     2
            "2.1.31.1.1.1.15",  # ifHighSpeed            .. 1000 means 1Gbit
            "2.1.2.2.1.8",  # ifOperStatus               4
            "2.1.31.1.1.1.6",  # ifHCInOctets            5
            "2.1.31.1.1.1.7",  # ifHCInUcastPkts         6
            "2.1.31.1.1.1.8",  # ifHCInMulticastPkts     7
            "2.1.31.1.1.1.9",  # ifHCInBroadcastPkts     8
            "2.1.2.2.1.13",  # ifInDiscards              9
            "2.1.2.2.1.14",  # ifInErrors               10
            "2.1.31.1.1.1.10",  # ifHCOutOctets         11
            "2.1.31.1.1.1.11",  # ifHCOutUcastPkts      12
            "2.1.31.1.1.1.12",  # ifHCOutMulticastPkts  13
            "2.1.31.1.1.1.13",  # ifHCOutBroadcastPkts  14
            "2.1.2.2.1.19",  # ifOutDiscards            15
            "2.1.2.2.1.20",  # ifOutErrors              16
            "2.1.2.2.1.21",  # ifOutQLen                17
            "4.1.11863.1.1.3.2.1.1.1.1.2",  # special for TP Link
            OIDBytes("2.1.2.2.1.6"),  # ifPhysAddress            19
            # Additionally fetch the standard OIDs for aliases.
            # Current tplink devices seem to support this OID and no longer the
            # ones under 4.1.11863.
            "2.1.31.1.1.1.18",  # ifAlias
        ],
    ),
    detect=all_of(contains(".1.3.6.1.2.1.1.2.0", ".4.1.11863."), if64.HAS_ifHCInOctets),
    supersedes=["if", "if64"],
)
