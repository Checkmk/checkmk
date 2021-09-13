#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore
checkname = "cisco_prime_wifi_connections"

# Create JSON string with this command in cisco_prime.include:
#    print("\n".join("'%s'" % line
#                    for line in json.dumps(
#                        {"queryResponse": {"entity": elements[:4]}}, indent=1)
#                    .split("\n")))
# Remember to remove sensitive data like names, addresses, ip/mac-addresses, serial numbers
info = [
    [
        "{"
        ' "queryResponse": {'
        '  "entity": ['
        "   {"
        '    "@dtoType": "clientCountsDTO",'
        '    "@type": "ClientCounts",'
        '    "@url": "https://hello.world.de/webacs/api/v1/data/ClientCounts/61671983180",'
        '    "clientCountsDTO": {'
        '     "@displayName": "61671983180",'
        '     "@id": "61671983180",'
        '     "authCount": 7247,'
        '     "collectionTime": 1494512992280,'
        '     "count": 7319,'
        '     "dot11aAuthCount": 1227,'
        '     "dot11aCount": 1243,'
        '     "dot11acAuthCount": 430,'
        '     "dot11acCount": 433,'
        '     "dot11bAuthCount": 0,'
        '     "dot11bCount": 0,'
        '     "dot11gAuthCount": 2400,'
        '     "dot11gCount": 2415,'
        '     "dot11n2_4AuthCount": 2253,'
        '     "dot11n2_4Count": 2280,'
        '     "dot11n5AuthCount": 937,'
        '     "dot11n5Count": 948,'
        '     "key": "All SSIDs",'
        '     "subkey": "ROOT-DOMAIN",'
        '     "type": "SSID",'
        '     "wgbAuthCount": 0,'
        '     "wgbCount": 0,'
        '     "wired100MAuthCount": 0,'
        '     "wired100MCount": 0,'
        '     "wired10MAuthCount": 0,'
        '     "wired10MCount": 0,'
        '     "wired1GAuthCount": 0,'
        '     "wired1GCount": 0'
        "    }"
        "   },"
        "   {"
        '    "@dtoType": "clientCountsDTO",'
        '    "@type": "ClientCounts",'
        '    "@url": "https://hello.world.de/webacs/api/v1/data/ClientCounts/61671983182",'
        '    "clientCountsDTO": {'
        '     "@displayName": "61671983182",'
        '     "@id": "61671983182",'
        '     "authCount": 75,'
        '     "collectionTime": 1494512992280,'
        '     "count": 78,'
        '     "dot11aAuthCount": 12,'
        '     "dot11aCount": 12,'
        '     "dot11acAuthCount": 5,'
        '     "dot11acCount": 5,'
        '     "dot11bAuthCount": 0,'
        '     "dot11bCount": 0,'
        '     "dot11gAuthCount": 24,'
        '     "dot11gCount": 25,'
        '     "dot11n2_4AuthCount": 20,'
        '     "dot11n2_4Count": 22,'
        '     "dot11n5AuthCount": 14,'
        '     "dot11n5Count": 14,'
        '     "key": "eduintern",'
        '     "subkey": "ROOT-DOMAIN",'
        '     "type": "SSID",'
        '     "wgbAuthCount": 0,'
        '     "wgbCount": 0,'
        '     "wired100MAuthCount": 0,'
        '     "wired100MCount": 0,'
        '     "wired10MAuthCount": 0,'
        '     "wired10MCount": 0,'
        '     "wired1GAuthCount": 0,'
        '     "wired1GCount": 0'
        "    }"
        "   },"
        "   {"
        '    "@dtoType": "clientCountsDTO",'
        '    "@type": "ClientCounts",'
        '    "@url": "https://hello.world.de/webacs/api/v1/data/ClientCounts/61671983190",'
        '    "clientCountsDTO": {'
        '     "@displayName": "61671983190",'
        '     "@id": "61671983190",'
        '     "authCount": 231,'
        '     "collectionTime": 1494512992280,'
        '     "count": 234,'
        '     "dot11aAuthCount": 31,'
        '     "dot11aCount": 31,'
        '     "dot11acAuthCount": 16,'
        '     "dot11acCount": 16,'
        '     "dot11bAuthCount": 0,'
        '     "dot11bCount": 0,'
        '     "dot11gAuthCount": 87,'
        '     "dot11gCount": 87,'
        '     "dot11n2_4AuthCount": 73,'
        '     "dot11n2_4Count": 75,'
        '     "dot11n5AuthCount": 24,'
        '     "dot11n5Count": 25,'
        '     "key": "eduinfo",'
        '     "subkey": "ROOT-DOMAIN",'
        '     "type": "SSID",'
        '     "wgbAuthCount": 0,'
        '     "wgbCount": 0,'
        '     "wired100MAuthCount": 0,'
        '     "wired100MCount": 0,'
        '     "wired10MAuthCount": 0,'
        '     "wired10MCount": 0,'
        '     "wired1GAuthCount": 0,'
        '     "wired1GCount": 0'
        "    }"
        "   },"
        "   {"
        '    "@dtoType": "clientCountsDTO",'
        '    "@type": "ClientCounts",'
        '    "@url": "https://hello.world.de/webacs/api/v1/data/ClientCounts/61671983195",'
        '    "clientCountsDTO": {'
        '     "@displayName": "61671983195",'
        '     "@id": "61671983195",'
        '     "authCount": 6941,'
        '     "collectionTime": 1494512992280,'
        '     "count": 7007,'
        '     "dot11aAuthCount": 1184,'
        '     "dot11aCount": 1200,'
        '     "dot11acAuthCount": 409,'
        '     "dot11acCount": 412,'
        '     "dot11bAuthCount": 0,'
        '     "dot11bCount": 0,'
        '     "dot11gAuthCount": 2289,'
        '     "dot11gCount": 2303,'
        '     "dot11n2_4AuthCount": 2160,'
        '     "dot11n2_4Count": 2183,'
        '     "dot11n5AuthCount": 899,'
        '     "dot11n5Count": 909,'
        '     "key": "eduroam",'
        '     "subkey": "ROOT-DOMAIN",'
        '     "type": "SSID",'
        '     "wgbAuthCount": 0,'
        '     "wgbCount": 0,'
        '     "wired100MAuthCount": 0,'
        '     "wired100MCount": 0,'
        '     "wired10MAuthCount": 0,'
        '     "wired10MCount": 0,'
        '     "wired1GAuthCount": 0,'
        '     "wired1GCount": 0'
        "    }"
        "   }"
        "  ]"
        " }"
        "}"
    ]
]

discovery = {"": [(None, {})]}

checks = {
    "": [
        (
            None,
            {},
            [
                (
                    0,
                    "Total connections: 7247",
                    [("wifi_connection_total", 7247, None, None, None, None)],
                ),
                (0, "802.11a: 1227", [("wifi_connection_dot11a", 1227, None, None, None, None)]),
                (0, "802.11b: 0", [("wifi_connection_dot11b", 0, None, None, None, None)]),
                (0, "802.11g: 2400", [("wifi_connection_dot11g", 2400, None, None, None, None)]),
                (0, "802.11ac: 430", [("wifi_connection_dot11ac", 430, None, None, None, None)]),
                (
                    0,
                    "802.11n24: 2253",
                    [("wifi_connection_dot11n2_4", 2253, None, None, None, None)],
                ),
                (0, "802.11n5: 937", [("wifi_connection_dot11n5", 937, None, None, None, None)]),
            ],
        ),
        (
            None,
            {"levels_lower": (20000, 10000)},
            [
                (
                    2,
                    "Total connections: 7247 (warn/crit below 20000/10000)",
                    [("wifi_connection_total", 7247, None, None, None, None)],
                ),
                (0, "802.11a: 1227", [("wifi_connection_dot11a", 1227, None, None, None, None)]),
                (0, "802.11b: 0", [("wifi_connection_dot11b", 0, None, None, None, None)]),
                (0, "802.11g: 2400", [("wifi_connection_dot11g", 2400, None, None, None, None)]),
                (0, "802.11ac: 430", [("wifi_connection_dot11ac", 430, None, None, None, None)]),
                (
                    0,
                    "802.11n24: 2253",
                    [("wifi_connection_dot11n2_4", 2253, None, None, None, None)],
                ),
                (0, "802.11n5: 937", [("wifi_connection_dot11n5", 937, None, None, None, None)]),
            ],
        ),
    ],
}
