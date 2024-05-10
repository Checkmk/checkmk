#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "f5_bigip_vserver"

mock_item_state = {
    "": {
        "connections_rate.0" : (0, 42),
        "if_out_pkts.0": (0, 42),
        "if_in_octets.0": (0, 32),
    },
}


info = [
    [
        "/Common/sight-seeing.wurmhole.univ",
        "1",
        "1",
        "The virtual server is available",
        "\xd4;xK",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "0",
        "",
    ],
    [
        "/Common/www.wurmhole.univ_HTTP2HTTPS",
        "4",
        "1",
        (
            "The children pool member(s) either don't"
            " have service checking enabled, or service check results are not available yet"
        ),
        "\xd4;xI",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "42",
        "0",
        "",
    ],
    [
        "/Common/sight-seeing.wurmhole.univ_HTTP2HTTPS",
        "4",
        "1",
        (
            "The children pool member(s) either"
            " don't have service checking enabled, or service check results are not available yet"
        ),
        "\xd4;xK",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "",
        "0",
        "",
    ],
    [
        "/Common/starfleet.space",
        "4",
        "",
        "To infinity and beyond!",
        "\xde\xca\xff\xed",
        "",
        "",
        "",
        "",
        "42",
        "32",
        "",
        "",
        "0",
        "",
    ],
]


discovery = {
    "": [
        ("/Common/sight-seeing.wurmhole.univ", {}),
        ("/Common/sight-seeing.wurmhole.univ_HTTP2HTTPS", {}),
        ("/Common/www.wurmhole.univ_HTTP2HTTPS", {}),
        ("/Common/starfleet.space", {}),
    ],
}


checks = {
    "": [
        (
            "/Common/sight-seeing.wurmhole.univ_HTTP2HTTPS",
            {},
            [
                (0, "Virtual Server with IP 212.59.120.75 is enabled", []),
                (
                    1,
                    (
                        "State availability is unknown, Detail: The children pool member(s) either"
                        " don't have service checking enabled, or service check results are not"
                        " available yet"
                    ),
                    [],
                ),
                (0, "Client connections: 0", [("connections", 0, None, None, None, None)]),
            ],
        ),
        ("/Common/www.wurmhole.univ", {}, []),
        (
            "/Common/www.wurmhole.univ_HTTP2HTTPS",
            {},
            [
                (0, "Virtual Server with IP 212.59.120.73 is enabled", []),
                (
                    1,
                    (
                        "State availability is unknown, Detail: The children pool member(s) either"
                        " don't have service checking enabled, or service check results are not"
                        " available yet"
                    ),
                    [],
                ),
                (
                    0,
                    "Client connections: 0",
                    [
                        ("connections", 0, None, None, None, None),
                        ("connections_rate", 0, None, None, None, None),
                    ],
                ),
                (0, "Connections rate: 0.00/sec", []),
            ],
        ),
        (
            "/Common/starfleet.space",
            {
                "if_in_octets": (-23, 42),
                "if_total_pkts_lower": (100, 200),
                "if_total_pkts": (300, 400),
            },
            [
                (1, "Virtual Server with IP 222.202.255.237 is in unknown state", []),
                (1, "State availability is unknown, Detail: To infinity and beyond!", []),
                (
                    0,
                    "Client connections: 0",
                    [
                        ("connections", 0, None, None, None, None),
                        ("if_in_octets", 0.0, None, None, None, None),
                        ("if_out_pkts", 0.0, None, None, None, None),
                        ("if_total_octets", 0.0, None, None, None, None),
                        ("if_total_pkts", 0.0, None, None, None, None),
                    ],
                ),
                (1, "Incoming bytes: 0.00 B/s (warn/crit at -23.0 B/s/42.0 B/s)", []),
                (2, "Total packets: 0.0/s (warn/crit below 100/s/200/s)", []),
            ],
        ),
    ],
}
