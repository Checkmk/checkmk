#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "ibm_svc_node"


info = [
    [
        "1",
        "N1_164191",
        "10001AA202",
        "500507680100D7CA",
        "online",
        "0",
        "io_grp0",
        "no",
        "2040000051442002",
        "CG8  ",
        "iqn.1986-03.com.ibm",
        "2145.svc-cl.n1164191",
        "",
        "164191",
        "",
        "",
        "",
        "",
        "",
    ],
    [
        "2",
        "N2_164373",
        "10001AA259",
        "500507680100D874",
        "online",
        "0",
        "io_grp0",
        "no",
        "2040000051442149",
        "CG8  ",
        "iqn.1986-03.com.ibm",
        "2145.svc-cl.n2164373",
        "",
        "164373",
        "",
        "",
        "",
        "",
        "",
    ],
    [
        "5",
        "N3_162711",
        "100025E317",
        "500507680100D0A7",
        "online",
        "1",
        "io_grp1",
        "no",
        "2040000085543047",
        "CG8  ",
        "iqn.1986-03.com.ibm",
        "2145.svc-cl.n3162711",
        "",
        "162711",
        "",
        "",
        "",
        "",
        "",
    ],
    [
        "6",
        "N4_164312",
        "100025E315",
        "500507680100D880",
        "online",
        "1",
        "io_grp1",
        "yes",
        "2040000085543045",
        "CG  8",
        "iqn.1986-03.com.ibm",
        "2145.svc-cl.n4164312",
        "",
        "164312",
        "",
        "",
        "",
        "",
        "",
    ],
]


discovery = {"": [("io_grp0", {}), ("io_grp1", {})]}


checks = {
    "": [
        ("io_grp0", {}, [(0, "Node N1_164191 is online, Node N2_164373 is online", [])]),
        ("io_grp1", {}, [(0, "Node N3_162711 is online, Node N4_164312 is online", [])]),
    ]
}
