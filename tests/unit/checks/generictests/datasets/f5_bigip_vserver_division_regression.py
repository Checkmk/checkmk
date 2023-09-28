#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "f5_bigip_vserver"

mock_item_state = {
    "": {
        "connections_rate.0" : (0, 2535),
        "if_in_pkts.0": (0, 70981),
        "if_out_pkts.0": (0, 84431),
        "if_in_octets.0": (0, 10961763),
        "if_out_octets.0": (0, 83403367),
        "packet_velocity_asic.0": (0, 0),
    },
}

info = [
    [
        "VS_BM",
        "1",
        "1",
        "The virtual server is available",
        "\xac\x14\xcad",
        "38",
        "76766",
        "10744",
        "70981",
        "84431",
        "10961763",
        "83403367",
        "2535",
        "0",
        "0",
    ],
]


discovery = {
    "": [
        ("VS_BM", {}),
    ]
}


checks = {
    "": [
        (
            "VS_BM",
            {},
            [
                (0, "Virtual Server with IP 172.20.202.100 is enabled", []),
                (0, "State is up and available, Detail: The virtual server is available", []),
                (
                    0,
                    "Client connections: 0",
                    [
                        ("connections", 0, None, None, None, None),
                        ("connections_duration_max", 76.766, None, None, None, None),
                        ("connections_duration_mean", 10.744, None, None, None, None),
                        ("connections_duration_min", 0.038, None, None, None, None),
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
