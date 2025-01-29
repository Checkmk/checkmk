#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.agent_based.v2 import exists, OIDBytes, SimpleSNMPSection, SNMPTree, StringByteTable
from cmk.plugins.lib import interfaces


def parse_if(
    string_table: StringByteTable,
) -> interfaces.Section[interfaces.InterfaceWithCounters]:
    return [
        interfaces.InterfaceWithCounters(
            interfaces.Attributes(
                index=str(line[0]),
                descr=str(line[1]),
                type=str(line[2]),
                speed=interfaces.saveint(line[3]),
                oper_status=str(line[4]),
                out_qlen=interfaces.saveint(line[15]),
                alias=str(line[1]),
                phys_address=line[16],
            ),
            interfaces.Counters(
                in_octets=interfaces.saveint(line[5]),
                in_ucast=interfaces.saveint(line[6]),
                in_mcast=interfaces.saveint(line[7]),
                in_bcast=0,
                in_disc=interfaces.saveint(line[8]),
                in_err=interfaces.saveint(line[9]),
                out_octets=interfaces.saveint(line[10]),
                out_ucast=interfaces.saveint(line[11]),
                out_mcast=0,
                out_bcast=interfaces.saveint(line[12]),
                out_disc=interfaces.saveint(line[13]),
                out_err=interfaces.saveint(line[14]),
            ),
        )
        for line in string_table
        if interfaces.saveint(line[0]) > 0
    ]


snmp_section_if = SimpleSNMPSection(
    name="if",
    parse_function=parse_if,
    parsed_section_name="interfaces",
    fetch=SNMPTree(
        base=".1.3.6.1.2.1.2.2.1",
        oids=[
            "1",  # ifIndex                  0
            "2",  # ifDescr                  1
            "3",  # ifType                   2
            "5",  # ifSpeed                  3
            "8",  # ifOperStatus             4
            "10",  # ifInOctets              5
            "11",  # ifInUcastPkts           6
            "12",  # ifInNUcastPkts          7
            "13",  # ifInDiscards            8
            "14",  # ifInErrors              9
            "16",  # ifOutOctets             10
            "17",  # ifOutUcastPkts          11
            "18",  # ifOutNUcastPkts         12
            "19",  # ifOutDiscards           13
            "20",  # ifOutErrors             14
            "21",  # ifOutQLen               15
            OIDBytes("6"),  # ifPhysAddress  16
        ],
    ),
    detect=exists(".1.3.6.1.2.1.2.2.1.*"),
)
