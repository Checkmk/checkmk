#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Result, Service, State
from cmk.plugins.collection.agent_based.cisco_secure import (
    check_cisco_secure,
    inventory_cisco_secure,
    parse_cisco_secure,
    Section,
)


def _section() -> Section:
    return parse_cisco_secure(
        [
            [
                ["83886080", "mgmt0", "2"],
                ["101191680", "sup-fc0", "1"],
                ["151060481", "Vlan1", "2"],
                ["369098752", "port-channel1", "1"],
                ["369098753", "port-channel2", "1"],
                ["369099904", "port-channel1153", "1"],
                ["369099905", "port-channel1154", "1"],
                ["369100049", "port-channel1298", "1"],
                ["369100054", "port-channel1303", "1"],
                ["369100057", "port-channel1306", "1"],
                ["369100059", "port-channel1308", "1"],
                ["369100062", "port-channel1311", "1"],
                ["369100068", "port-channel1317", "1"],
                ["369100071", "port-channel1320", "2"],
                ["369100077", "port-channel1326", "2"],
                ["369100081", "port-channel1330", "1"],
                ["369100085", "port-channel1334", "2"],
                ["369100087", "port-channel1336", "1"],
                ["369100091", "port-channel1340", "1"],
                ["369100093", "port-channel1342", "1"],
                ["369100097", "port-channel1346", "1"],
                ["369100099", "port-channel1348", "1"],
                ["369100101", "port-channel1350", "1"],
                ["436207616", "Ethernet1/1", "1"],
                ["436211712", "Ethernet1/2", "1"],
                ["436215808", "Ethernet1/3", "1"],
                ["436219904", "Ethernet1/4", "1"],
                ["436224000", "Ethernet1/5", "1"],
                ["436228096", "Ethernet1/6", "1"],
                ["436232192", "Ethernet1/7", "1"],
                ["436236288", "Ethernet1/8", "1"],
                ["436240384", "Ethernet1/9", "2"],
                ["436244480", "Ethernet1/10", "2"],
                ["436248576", "Ethernet1/11", "2"],
                ["436252672", "Ethernet1/12", "2"],
                ["436256768", "Ethernet1/13", "2"],
                ["436260864", "Ethernet1/14", "2"],
                ["436264960", "Ethernet1/15", "2"],
                ["436269056", "Ethernet1/16", "2"],
                ["436273152", "Ethernet1/17", "1"],
                ["436277248", "Ethernet1/18", "1"],
                ["436281344", "Ethernet1/19", "2"],
                ["436285440", "Ethernet1/20", "2"],
                ["436289536", "Ethernet1/21", "1"],
                ["436293632", "Ethernet1/22", "1"],
                ["436297728", "Ethernet1/23", "2"],
                ["436301824", "Ethernet1/24", "2"],
                ["436305920", "Ethernet1/25", "2"],
                ["436310016", "Ethernet1/26", "2"],
                ["436314112", "Ethernet1/27", "2"],
                ["436318208", "Ethernet1/28", "2"],
                ["436322304", "Ethernet1/29", "2"],
                ["436326400", "Ethernet1/30", "2"],
                ["436330496", "Ethernet1/31", "2"],
                ["436334592", "Ethernet1/32", "2"],
                ["469775264", "Vethernet827", "1"],
                ["469775296", "Vethernet829", "1"],
                ["469775392", "Vethernet835", "1"],
                ["469775424", "Vethernet837", "1"],
                ["469775696", "Vethernet854", "1"],
                ["469775760", "Vethernet858", "1"],
                ["469776528", "Vethernet906", "1"],
                ["469776608", "Vethernet911", "1"],
                ["469776640", "Vethernet913", "1"],
                ["469776720", "Vethernet918", "2"],
                ["469777888", "Vethernet991", "1"],
                ["469777920", "Vethernet993", "1"],
                ["469778192", "Vethernet1010", "1"],
                ["469778208", "Vethernet1011", "1"],
                ["469778240", "Vethernet1013", "1"],
                ["469778480", "Vethernet1028", "1"],
                ["469778496", "Vethernet1029", "1"],
                ["469778528", "Vethernet1031", "1"],
                ["469778576", "Vethernet1034", "1"],
                ["469778592", "Vethernet1035", "1"],
                ["469778624", "Vethernet1037", "1"],
                ["469778672", "Vethernet1040", "1"],
                ["469778688", "Vethernet1041", "1"],
                ["469778720", "Vethernet1043", "1"],
                ["469778976", "Vethernet1059", "1"],
                ["469779008", "Vethernet1061", "1"],
                ["469779056", "Vethernet1064", "1"],
                ["469779072", "Vethernet1065", "1"],
                ["469779104", "Vethernet1067", "1"],
                ["469779312", "Vethernet1080", "1"],
                ["469779456", "Vethernet1089", "1"],
                ["469779488", "Vethernet1091", "1"],
                ["469779536", "Vethernet1094", "1"],
                ["469779552", "Vethernet1095", "1"],
                ["469779584", "Vethernet1097", "1"],
                ["469780176", "Vethernet1134", "1"],
                ["469780288", "Vethernet1141", "1"],
                ["469780320", "Vethernet1143", "1"],
                ["469780368", "Vethernet1146", "1"],
                ["469780384", "Vethernet1147", "1"],
                ["469780416", "Vethernet1149", "1"],
                ["469780496", "Vethernet1154", "1"],
                ["469906432", "Vethernet9025", "1"],
                ["469906560", "Vethernet9033", "1"],
                ["469906816", "Vethernet9049", "1"],
                ["469906880", "Vethernet9053", "1"],
                ["469907648", "Vethernet9101", "1"],
                ["469907776", "Vethernet9109", "1"],
                ["469907840", "Vethernet9113", "2"],
                ["469909056", "Vethernet9189", "1"],
                ["469910208", "Vethernet9261", "1"],
                ["469910432", "Vethernet9275", "1"],
                ["469910688", "Vethernet9291", "1"],
                ["469911296", "Vethernet9329", "1"],
                ["469911520", "Vethernet9343", "1"],
                ["469911616", "Vethernet9349", "1"],
                ["503317202", "vfc723", "1"],
                ["503317312", "vfc833", "1"],
                ["503317320", "vfc841", "1"],
                ["503317336", "vfc857", "1"],
                ["503317340", "vfc861", "1"],
                ["503317388", "vfc909", "1"],
                ["503317396", "vfc917", "1"],
                ["503317400", "vfc921", "2"],
                ["503317476", "vfc997", "1"],
                ["503317548", "vfc1069", "1"],
                ["503317562", "vfc1083", "1"],
                ["503317578", "vfc1099", "1"],
                ["503317616", "vfc1137", "1"],
                ["503317630", "vfc1151", "1"],
                ["503317636", "vfc1157", "1"],
                ["520093696", "Ethernet1/1/1", "1"],
                ["520093760", "Ethernet1/1/2", "2"],
                ["520093824", "Ethernet1/1/3", "1"],
                ["520093888", "Ethernet1/1/4", "2"],
                ["520093952", "Ethernet1/1/5", "1"],
                ["520094016", "Ethernet1/1/6", "2"],
                ["520094080", "Ethernet1/1/7", "1"],
                ["520094144", "Ethernet1/1/8", "2"],
                ["520094208", "Ethernet1/1/9", "1"],
                ["520094272", "Ethernet1/1/10", "2"],
                ["520094336", "Ethernet1/1/11", "1"],
                ["520094400", "Ethernet1/1/12", "2"],
                ["520094464", "Ethernet1/1/13", "1"],
                ["520094528", "Ethernet1/1/14", "2"],
                ["520094592", "Ethernet1/1/15", "1"],
                ["520094656", "Ethernet1/1/16", "2"],
                ["520094720", "Ethernet1/1/17", "1"],
                ["520094784", "Ethernet1/1/18", "2"],
                ["520094848", "Ethernet1/1/19", "1"],
                ["520094912", "Ethernet1/1/20", "2"],
                ["520094976", "Ethernet1/1/21", "1"],
                ["520095040", "Ethernet1/1/22", "2"],
                ["520095104", "Ethernet1/1/23", "1"],
                ["520095168", "Ethernet1/1/24", "2"],
                ["520095232", "Ethernet1/1/25", "1"],
                ["520095296", "Ethernet1/1/26", "2"],
                ["520095360", "Ethernet1/1/27", "1"],
                ["520095424", "Ethernet1/1/28", "2"],
                ["520095488", "Ethernet1/1/29", "1"],
                ["520095552", "Ethernet1/1/30", "2"],
                ["520095616", "Ethernet1/1/31", "1"],
                ["520095680", "Ethernet1/1/32", "2"],
                ["520095744", "Ethernet1/1/33", "1"],
                ["520159232", "Ethernet2/1/1", "1"],
                ["520159296", "Ethernet2/1/2", "2"],
                ["520159360", "Ethernet2/1/3", "1"],
                ["520159424", "Ethernet2/1/4", "2"],
                ["520159488", "Ethernet2/1/5", "1"],
                ["520159552", "Ethernet2/1/6", "2"],
                ["520159616", "Ethernet2/1/7", "1"],
                ["520159680", "Ethernet2/1/8", "2"],
                ["520159744", "Ethernet2/1/9", "1"],
                ["520159808", "Ethernet2/1/10", "2"],
                ["520159872", "Ethernet2/1/11", "1"],
                ["520159936", "Ethernet2/1/12", "2"],
                ["520160000", "Ethernet2/1/13", "1"],
                ["520160064", "Ethernet2/1/14", "2"],
                ["520160128", "Ethernet2/1/15", "1"],
                ["520160192", "Ethernet2/1/16", "2"],
                ["520160256", "Ethernet2/1/17", "2"],
                ["520160320", "Ethernet2/1/18", "2"],
                ["520160384", "Ethernet2/1/19", "2"],
                ["520160448", "Ethernet2/1/20", "2"],
                ["520160512", "Ethernet2/1/21", "2"],
                ["520160576", "Ethernet2/1/22", "2"],
                ["520160640", "Ethernet2/1/23", "2"],
                ["520160704", "Ethernet2/1/24", "2"],
                ["520160768", "Ethernet2/1/25", "1"],
                ["520160832", "Ethernet2/1/26", "2"],
                ["520160896", "Ethernet2/1/27", "1"],
                ["520160960", "Ethernet2/1/28", "2"],
                ["520161024", "Ethernet2/1/29", "2"],
                ["520161088", "Ethernet2/1/30", "2"],
                ["520161152", "Ethernet2/1/31", "2"],
                ["520161216", "Ethernet2/1/32", "2"],
                ["520161280", "Ethernet2/1/33", "1"],
            ],
            [
                ["469775392", "", "3", "", ""],
                ["469775424", "", "3", "", ""],
                ["469775696", "", "3", "", ""],
                ["469775760", "", "3", "", ""],
                ["469776528", "", "3", "", ""],
                ["469776608", "2", "3", "0", ""],
                ["469776640", "2", "3", "0", ""],
                ["469776720", "2", "3", "0", ""],
                ["469777888", "2", "3", "0", ""],
                ["469777920", "2", "3", "0", ""],
                ["469778192", "2", "3", "0", ""],
                ["469778208", "2", "3", "0", ""],
                ["469778240", "2", "3", "0", ""],
                ["469778480", "2", "3", "0", ""],
                ["469778496", "2", "3", "0", ""],
                ["469778528", "2", "3", "0", ""],
                ["469778576", "2", "3", "0", ""],
                ["469778592", "2", "3", "0", ""],
                ["469778624", "2", "3", "0", ""],
                ["469778672", "2", "3", "0", ""],
                ["469778688", "2", "3", "0", ""],
                ["469778720", "2", "3", "0", ""],
                ["469778976", "2", "3", "0", ""],
                ["469779008", "2", "3", "0", ""],
                ["469779056", "2", "3", "0", ""],
                ["469779072", "2", "3", "0", ""],
                ["469779104", "2", "3", "0", ""],
                ["469779312", "2", "3", "0", ""],
                ["469779456", "2", "3", "0", ""],
                ["469779488", "2", "3", "0", ""],
                ["469779536", "2", "3", "0", ""],
                ["469779552", "2", "3", "0", ""],
                ["469779584", "2", "3", "0", ""],
                ["469780176", "2", "3", "0", ""],
                ["469780288", "2", "3", "0", ""],
                ["469780320", "2", "3", "0", ""],
                ["469780368", "2", "3", "0", ""],
                ["469780384", "2", "3", "0", ""],
                ["469780416", "2", "3", "0", ""],
                ["469780496", "2", "3", "0", ""],
                ["520093760", "2", "3", "0", ""],
                ["520093888", "2", "3", "0", ""],
                ["520094016", "2", "3", "0", ""],
                ["520094144", "2", "3", "0", ""],
                ["520094272", "2", "3", "0", ""],
                ["520094400", "2", "3", "0", ""],
                ["520094528", "2", "3", "0", ""],
                ["520094656", "2", "3", "0", ""],
                ["520094784", "2", "3", "0", ""],
                ["520094912", "2", "3", "0", ""],
                ["520095040", "2", "3", "0", ""],
                ["520095168", "2", "3", "0", ""],
                ["520095296", "2", "3", "0", ""],
                ["520095424", "2", "3", "0", ""],
                ["520095552", "2", "3", "0", ""],
                ["520095680", "2", "3", "0", ""],
                ["520159296", "2", "3", "0", ""],
                ["520159424", "2", "3", "0", ""],
                ["520159552", "2", "3", "0", ""],
                ["520159680", "2", "3", "0", ""],
                ["520159808", "2", "3", "0", ""],
                ["520159936", "2", "3", "0", ""],
                ["520160064", "2", "3", "0", ""],
                ["520160192", "2", "3", "0", ""],
                ["520160320", "2", "3", "0", ""],
                ["520160448", "2", "3", "0", ""],
                ["520160576", "2", "3", "0", ""],
                ["520160704", "2", "3", "0", ""],
                ["520160832", "2", "3", "0", ""],
                ["520160960", "2", "3", "0", ""],
                ["520161088", "2", "3", "0", ""],
                ["520161216", "2", "3", "0", ""],
            ],
        ]
    )


def test_discovery_cisco_secure() -> None:
    assert list(inventory_cisco_secure(_section())) == [Service()] * 72


def test_check_cisco_secure() -> None:
    results = list(check_cisco_secure(_section()))
    assert len(results) == 72
    assert results[40] == Result(
        state=State.CRIT,
        summary=(
            "Port Ethernet1/1/2: shutdown due to security violation (violation count: 0, last MAC: )"
        ),
    )


def _section_unknown() -> Section:
    return parse_cisco_secure(
        [
            [
                ["16777216", "fc1/1", "1"],
                ["16781312", "fc1/2", "1"],
                ["16785408", "fc1/3", "2"],
                ["16789504", "fc1/4", "2"],
                ["16793600", "fc1/5", "2"],
                ["16797696", "fc1/6", "2"],
                ["83886080", "mgmt0", "2"],
                ["151060481", "Vlan1", "2"],
                ["369098754", "port-channel3", "1"],
                ["369100040", "port-channel1289", "1"],
                ["369100041", "port-channel1290", "1"],
                ["369100042", "port-channel1291", "1"],
                ["436232192", "Ethernet1/7", "2"],
                ["436236288", "Ethernet1/8", "2"],
                ["436240384", "Ethernet1/9", "2"],
                ["436244480", "Ethernet1/10", "2"],
                ["436248576", "Ethernet1/11", "2"],
                ["436252672", "Ethernet1/12", "2"],
                ["436256768", "Ethernet1/13", "2"],
                ["436260864", "Ethernet1/14", "2"],
                ["436264960", "Ethernet1/15", "1"],
                ["436269056", "Ethernet1/16", "1"],
                ["436273152", "Ethernet1/17", "1"],
                ["436277248", "Ethernet1/18", "1"],
                ["436281344", "Ethernet1/19", "2"],
                ["436285440", "Ethernet1/20", "2"],
                ["436289536", "Ethernet1/21", "2"],
                ["436293632", "Ethernet1/22", "2"],
                ["436297728", "Ethernet1/23", "2"],
                ["436301824", "Ethernet1/24", "2"],
                ["436305920", "Ethernet1/25", "2"],
                ["436310016", "Ethernet1/26", "2"],
                ["436314112", "Ethernet1/27", "2"],
                ["436318208", "Ethernet1/28", "2"],
                ["436322304", "Ethernet1/29", "2"],
                ["436326400", "Ethernet1/30", "2"],
                ["436330496", "Ethernet1/31", "2"],
                ["436334592", "Ethernet1/32", "2"],
                ["436338688", "Ethernet1/33", "2"],
                ["436342784", "Ethernet1/34", "2"],
                ["436346880", "Ethernet1/35", "2"],
                ["436350976", "Ethernet1/36", "2"],
                ["436355072", "Ethernet1/37", "2"],
                ["436359168", "Ethernet1/38", "2"],
                ["436363264", "Ethernet1/39", "2"],
                ["436367360", "Ethernet1/40", "2"],
                ["469773120", "Vethernet693", "1"],
                ["469773184", "Vethernet697", "1"],
                ["469773248", "Vethernet701", "1"],
                ["469904224", "Vethernet8887", "1"],
                ["469904288", "Vethernet8891", "1"],
                ["469904352", "Vethernet8895", "1"],
                ["503317174", "vfc695", "1"],
                ["503317178", "vfc699", "1"],
                ["503317182", "vfc703", "1"],
                ["520093760", "Ethernet1/1/2", "2"],
                ["520093824", "Ethernet1/1/3", "1"],
                ["520093888", "Ethernet1/1/4", "2"],
                ["520093952", "Ethernet1/1/5", "1"],
                ["520094016", "Ethernet1/1/6", "2"],
                ["520094080", "Ethernet1/1/7", "1"],
                ["520094144", "Ethernet1/1/8", "2"],
                ["520094208", "Ethernet1/1/9", "1"],
                ["520094272", "Ethernet1/1/10", "2"],
                ["520094336", "Ethernet1/1/11", "1"],
                ["520094400", "Ethernet1/1/12", "2"],
                ["520094464", "Ethernet1/1/13", "2"],
                ["520094528", "Ethernet1/1/14", "2"],
                ["520094592", "Ethernet1/1/15", "2"],
                ["520094656", "Ethernet1/1/16", "2"],
                ["520094720", "Ethernet1/1/17", "2"],
                ["520094784", "Ethernet1/1/18", "2"],
                ["520094848", "Ethernet1/1/19", "2"],
                ["520094912", "Ethernet1/1/20", "2"],
                ["520094976", "Ethernet1/1/21", "2"],
                ["520095040", "Ethernet1/1/22", "2"],
                ["520095104", "Ethernet1/1/23", "2"],
                ["520095168", "Ethernet1/1/24", "2"],
                ["520095232", "Ethernet1/1/25", "2"],
                ["520095296", "Ethernet1/1/26", "2"],
                ["520095360", "Ethernet1/1/27", "2"],
                ["520095424", "Ethernet1/1/28", "2"],
                ["520095488", "Ethernet1/1/29", "2"],
                ["520095552", "Ethernet1/1/30", "2"],
                ["520095616", "Ethernet1/1/31", "2"],
                ["520095680", "Ethernet1/1/32", "2"],
                ["520095744", "Ethernet1/1/33", "1"],
            ],
            [
                ["469773120", "", "", "0", ""],
                ["469773184", "", "", "0", ""],
                ["469773248", "", "3", "0", ""],
                ["520093760", "", "3", "0", ""],
                ["520093888", "2", "3", "0", ""],
                ["520094016", "2", "3", "0", ""],
                ["520094144", "2", "3", "0", ""],
                ["520094272", "2", "3", "0", ""],
                ["520094400", "2", "3", "0", ""],
                ["520094784", "2", "3", "0", ""],
                ["520094912", "2", "3", "0", ""],
            ],
        ]
    )


def test_check_cisco_secure_unknown() -> None:
    results = list(check_cisco_secure(_section_unknown()))
    assert len(results) == 11
    assert results[0] == Result(
        state=State.UNKNOWN,
        summary=(
            "Port Vethernet693: unknown (violation count: 0, last MAC: ) unknown enabled state"
        ),
    )
