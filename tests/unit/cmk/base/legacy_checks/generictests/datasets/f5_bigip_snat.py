#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code=var-annotated

checkname = "f5_bigip_snat"

mock_item_state = {
    "": {
        "connections_rate.0": (0, 7),
        "if_in_pkts.0": (0, 10),
        "if_out_pkts.0": (0, 712),
        "if_in_octets.0": (0, 5),
        "if_out_octets.0": (0, 236),
        # "packet_velocity_asic.0": (0, 0),
    },
}

info = [
    ["SQL", "3", "120", "0", "0", "3", "0"],
    ["MI-VSP", "2559", "267523", "2216", "2134447", "167", "0"],
    ["RS6000", "31", "1296", "31", "1264", "25", "0"],
    ["LS_Test", "0", "0", "0", "0", "0", "0"],
    ["foobar", "2221", "2226331", "1509", "729471", "79", "0"],
    ["keycomp", "2534239", "2132789593", "2490959", "1972334953", "464", "2"],
    ["AS400_20", "304980", "103809944", "268938", "39785918", "22631", "10"],
    ["AS400_21", "0", "0", "0", "0", "0", "0"],
    ["keycomp2", "183", "32988", "168", "73366", "12", "0"],
    ["websrvc2", "0", "0", "0", "0", "0", "0"],
    ["AS2_proxy", "10", "712", "5", "236", "7", "0"],
    ["MI-SENTRY", "0", "0", "0", "0", "0", "0"],
    ["Outbound_SNAT", "160631017", "30383696271", "217420496", "220088423650", "8870002", "8279"],
    ["foo.bar.com", "0", "0", "0", "0", "0", "0"],
    ["baz.buz.com", "45412", "57683523", "26828", "6379159", "462", "0"],
    ["wuz.huz-kuz.com", "0", "0", "0", "0", "0", "0"],
    ["bar.foo.com", "339", "13560", "7", "280", "339", "0"],
    ["foo.bar.buz-huz.com", "0", "0", "0", "0", "0", "0"],
]

discovery = {
    "": [
        ("AS2_proxy", {}),
        ("AS400_20", {}),
        ("AS400_21", {}),
        ("LS_Test", {}),
        ("MI-SENTRY", {}),
        ("MI-VSP", {}),
        ("Outbound_SNAT", {}),
        ("RS6000", {}),
        ("SQL", {}),
        ("bar.foo.com", {}),
        ("baz.buz.com", {}),
        ("foo.bar.buz-huz.com", {}),
        ("foo.bar.com", {}),
        ("foobar", {}),
        ("keycomp", {}),
        ("keycomp2", {}),
        ("websrvc2", {}),
        ("wuz.huz-kuz.com", {}),
    ]
}

checks = {
    "": [
        (
            "AS2_proxy",
            {},
            [
                (
                    0,
                    "Client connections: 0",
                    [
                        ("if_in_pkts", 0.0, None, None, None, None),
                        ("if_out_pkts", 0.0, None, None, None, None),
                        ("if_in_octets", 0.0, None, None, None, None),
                        ("if_out_octets", 0.0, None, None, None, None),
                        ("connections_rate", 0.0, None, None, None, None),
                        ("connections", 0, None, None, None, None),
                    ],
                ),
                (0, "Rate: 0.00/sec", []),
            ],
        ),
    ]
}
