#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated
checkname = "f5_bigip_vserver"

mock_item_state = {
    "": {
        "connections_rate.0" : (0, 0),
        "if_in_pkts.0": (0, 0),
        "if_out_pkts.0": (0, 0),
        "if_in_octets.0": (0, 0),
        "if_out_octets.0": (0, 0),
        "packet_velocity_asic.0": (0, 0),
    },
}

info = [
    [
        "/Common/vc_access.test.ch",
        "4",
        "2",
        "The children pool member(s) either don't have service checking enabled, or service check results are not available yet",
        "Á\x082\x86",
        "0",
        "0",
        "0",
        "0",
        "0",
        "0",
        "0",
        "0",
        "0",
        "0",
    ],
    [
        "/Common/vs_access_test.com",
        "4",
        "1",
        "The children pool member(s) either don't have service checking enabled, or service check results are not available yet",
        "Á\x082\x89",
        "13",
        "2278332",
        "339537",
        "347652",
        "599569",
        "37857905",
        "350096834",
        "1611",
        "0",
        "0",
    ],
    [
        "/Common/vs_travel.test.com",
        "4",
        "1",
        "The children pool member(s) either don't have service checking enabled, or service check results are not available yet",
        "Á\x082\x87",
        "79",
        "1147634",
        "48323",
        "58413",
        "82099",
        "5718595",
        "39981268",
        "164",
        "0",
        "0",
    ],
    [
        "/Common/vs_access-start.test.com",
        "4",
        "1",
        "The children pool member(s) either don't have service checking enabled, or service check results are not available yet",
        "Á\x082\x88",
        "0",
        "0",
        "0",
        "0",
        "0",
        "0",
        "0",
        "0",
        "0",
        "0",
    ],
]

discovery = {
    "": [
        ("/Common/vc_access.test.ch", {}),
        ("/Common/vs_access-start.test.com", {}),
        ("/Common/vs_access_test.com", {}),
        ("/Common/vs_travel.test.com", {}),
    ]
}

checks = {
    "": [
        (
            "/Common/vc_access.test.ch",
            {},
            [
                (0, "Virtual Server with IP 193.8.50.134 is disabled", []),
                (
                    1,
                    "State availability is unknown, Detail: The children pool member(s) either don't have service checking enabled, or service check results are not available yet",
                    [],
                ),
                (
                    0,
                    "Client connections: 0",
                    [
                        ("connections", 0, None, None, None, None),
                        ("connections_duration_max", 0, None, None, None, None),
                        ("connections_duration_mean", 0.0, None, None, None, None),
                        ("connections_duration_min", 0, None, None, None, None),
                        ("connections_rate", 0.0, None, None, None, None),
                        ("if_in_octets", 0.0, None, None, None, None),
                        ("if_in_pkts", 0.0, None, None, None, None),
                        ("if_out_octets", 0.0, None, None, None, None),
                        ("if_out_pkts", 0.0, None, None, None, None),
                        ("if_total_octets", 0.0, None, None, None, None),
                        ("if_total_pkts", 0.0, None, None, None, None),
                        ("packet_velocity_asic", 0.0, None, None, None, None),
                    ],
                ),
                (0, "Connections rate: 0.00/sec", []),
            ],
        ),
    ]
}
