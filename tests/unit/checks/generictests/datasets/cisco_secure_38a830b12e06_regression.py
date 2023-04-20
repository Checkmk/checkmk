#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# type: ignore


checkname = "cisco_secure"


info = [
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


discovery = {"": [(None, None)]}


checks = {
    "": [
        (
            None,
            {},
            [
                (
                    3,
                    "Port Vethernet693: unknown (violation count: 0, last MAC: ) unknown enabled state",
                    [],
                ),
                (
                    3,
                    "Port Vethernet697: unknown (violation count: 0, last MAC: ) unknown enabled state",
                    [],
                ),
                (
                    3,
                    "Port Vethernet701: shutdown due to security violation (violation count: 0, last MAC: ) unknown enabled state",
                    [],
                ),
                (
                    3,
                    "Port Ethernet1/1/2: shutdown due to security violation (violation count: 0, last MAC: ) unknown enabled state",
                    [],
                ),
                (
                    2,
                    "Port Ethernet1/1/4: shutdown due to security violation (violation count: 0, last MAC: )",
                    [],
                ),
                (
                    2,
                    "Port Ethernet1/1/6: shutdown due to security violation (violation count: 0, last MAC: )",
                    [],
                ),
                (
                    2,
                    "Port Ethernet1/1/8: shutdown due to security violation (violation count: 0, last MAC: )",
                    [],
                ),
                (
                    2,
                    "Port Ethernet1/1/10: shutdown due to security violation (violation count: 0, last MAC: )",
                    [],
                ),
                (
                    2,
                    "Port Ethernet1/1/12: shutdown due to security violation (violation count: 0, last MAC: )",
                    [],
                ),
                (
                    2,
                    "Port Ethernet1/1/18: shutdown due to security violation (violation count: 0, last MAC: )",
                    [],
                ),
                (
                    2,
                    "Port Ethernet1/1/20: shutdown due to security violation (violation count: 0, last MAC: )",
                    [],
                ),
            ],
        )
    ]
}
