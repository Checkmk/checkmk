#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated

checkname = "msexch_autodiscovery"


mock_item_state = {
    "": {
        "RequestsPersec_": (0, 19086),
    },
}


info = [
    [
        "Caption",
        "Description",
        "ErrorResponses",
        "ErrorResponsesPersec",
        "Frequency_Object",
        "Frequency_PerfTime",
        "Frequency_Sys100NS",
        "Name",
        "ProcessID",
        "RequestsPersec",
        "Timestamp_Object",
        "Timestamp_PerfTime",
        "Timestamp_Sys100NS",
        "TotalRequests",
    ],
    [
        "",
        "",
        "0",
        "0",
        "0",
        "2343747",
        "10000000",
        "",
        "29992",
        "19086",
        "0",
        "1025586529184",
        "131287884132350000",
        "19086",
    ],
]

discovery = {"": [(None, {})]}

checks = {
    "": [
        (None, {}, [(0, "Requests/sec: 0.00", [("requests_per_sec", 0.0, None, None, None, None)])])
    ]
}
