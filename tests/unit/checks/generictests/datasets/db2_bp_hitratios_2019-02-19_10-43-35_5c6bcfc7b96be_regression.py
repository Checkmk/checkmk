#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "db2_bp_hitratios"


info = [
    ["[[[serv0:ABC]]]"],
    ["node", "0", "foo1.bar2.baz3", "0"],
    [
        "BP_NAME",
        "TOTAL_HIT_RATIO_PERCENT",
        "DATA_HIT_RATIO_PERCENT",
        "INDEX_HIT_RATIO_PERCENT",
        "XDA_HIT_RATIO_PERCENT",
    ],
    ["IBMDEFAULTBP", "83.62", "78.70", "99.74", "50.00"],
    ["[[[serv1:XYZ]]]"],
    ["node", "0", "foo1.bar2.baz3", "0"],
]


discovery = {"": [("serv0:ABC DPF 0 foo1.bar2.baz3 0:IBMDEFAULTBP", {})]}


checks = {
    "": [
        (
            "serv0:ABC DPF 0 foo1.bar2.baz3 0:IBMDEFAULTBP",
            {},
            [
                (0, "Total: 83.62%", [("total_hitratio", 83.62, None, None, 0, 100)]),
                (0, "Data: 78.70%", [("data_hitratio", 78.7, None, None, 0, 100)]),
                (0, "Index: 99.74%", [("index_hitratio", 99.74, None, None, 0, 100)]),
                (0, "XDA: 50.00%", [("xda_hitratio", 50.0, None, None, 0, 100)]),
            ],
        )
    ]
}
