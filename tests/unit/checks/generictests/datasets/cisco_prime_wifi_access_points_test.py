#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore
checkname = "cisco_prime_wifi_access_points"

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
        '    "@dtoType": "accessPointsDTO",'
        '    "@type": "AccessPoints",'
        '    "@url": "https://hello.world.de/webacs/api/v1/data/AccessPoints/2101795",'
        '    "accessPointsDTO": {'
        '     "@displayName": "2101795",'
        '     "@id": "2101795",'
        '     "adminStatus": "ENABLE",'
        '     "clientCount": 0,'
        '     "clientCount_2_4GHz": 0,'
        '     "clientCount_5GHz": 0,'
        '     "controllerName": "wism22",'
        '     "countryCode": "DE",'
        '     "hreapEnabled": false,'
        '     "location": "default location",'
        '     "lwappUpTime": 70343302,'
        '     "model": "AIR-LAP1131AG-E-K9",'
        '     "softwareVersion": "8.0.152.12",'
        '     "status": "CLEARED",'
        '     "type": "AP1130",'
        '     "upTime": 125852602'
        "    }"
        "   },"
        "   {"
        '    "@dtoType": "accessPointsDTO",'
        '    "@type": "AccessPoints",'
        '    "@url": "https://hello.world.de/webacs/api/v1/data/AccessPoints/40164274",'
        '    "accessPointsDTO": {'
        '     "@displayName": "40164274",'
        '     "@id": "40164274",'
        '     "adminStatus": "ENABLE",'
        '     "clientCount": 0,'
        '     "clientCount_2_4GHz": 0,'
        '     "clientCount_5GHz": 0,'
        '     "controllerName": "wism21",'
        '     "countryCode": "DE",'
        '     "hreapEnabled": false,'
        '     "lwappUpTime": 126151608,'
        '     "model": "AIR-LAP1131AG-E-K9",'
        '     "serialNumber": "FCZ1046Q143",'
        '     "softwareVersion": "8.0.152.12",'
        '     "status": "CLEARED",'
        '     "type": "AP1130",'
        '     "upTime": 126158708'
        "    }"
        "   },"
        "   {"
        '    "@dtoType": "accessPointsDTO",'
        '    "@type": "AccessPoints",'
        '    "@url": "https://hello.world.de/webacs/api/v1/data/AccessPoints/40164277",'
        '    "accessPointsDTO": {'
        '     "@displayName": "40164277",'
        '     "@id": "40164277",'
        '     "adminStatus": "ENABLE",'
        '     "bootVersion": "12.3.2.4",'
        '     "clientCount": 0,'
        '     "clientCount_2_4GHz": 0,'
        '     "clientCount_5GHz": 0,'
        '     "countryCode": "DE",'
        '     "hreapEnabled": false,'
        '     "lwappUpTime": 3638416300,'
        '     "model": "AIR-LAP1231G-E-K9    ",'
        '     "softwareVersion": "7.0.252.0",'
        '     "status": "CRITICAL",'
        '     "type": "AP1200",'
        '     "upTime": 941477604'
        "    }"
        "   },"
        "   {"
        '    "@dtoType": "accessPointsDTO",'
        '    "@type": "AccessPoints",'
        '    "@url": "https://hello.world.de/webacs/api/v1/data/AccessPoints/59467791",'
        '    "accessPointsDTO": {'
        '     "@displayName": "59467791",'
        '     "@id": "59467791",'
        '     "adminStatus": "ENABLE",'
        '     "bootVersion": "1.2.3.4",'
        '     "clientCount": 4,'
        '     "clientCount_2_4GHz": 3,'
        '     "clientCount_5GHz": 1,'
        '     "controllerName": "wism22",'
        '     "countryCode": "DE",'
        '     "hreapEnabled": false,'
        '     "location": "Daheim",'
        '     "lwappUpTime": 70336104,'
        '     "model": "AIR-LAP1242AG-E-K9",'
        '     "softwareVersion": "8.0.152.12",'
        '     "status": "CLEARED",'
        '     "type": "AP1240",'
        '     "upTime": 125766504'
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
                    "Percent Critical: 25.0%",
                    [
                        ("ap_devices_percent_unhealthy", 25.0, None, None, None, None),
                    ],
                ),
                (0, "Cleared: 3", [("ap_devices_cleared", 3, None, None, None, None)]),
                (0, "Critical: 1", [("ap_devices_critical", 1, None, None, None, None)]),
            ],
        ),
        (
            None,
            {"levels": (20, 40)},
            [
                (
                    1,
                    "Percent Critical: 25.0% (warn/crit at 20.0%/40.0%)",
                    [("ap_devices_percent_unhealthy", 25.0, 20.0, 40.0, None, None)],
                ),
                (0, "Cleared: 3", [("ap_devices_cleared", 3, None, None, None, None)]),
                (0, "Critical: 1", [("ap_devices_critical", 1, None, None, None, None)]),
            ],
        ),
    ],
}
