#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "splunk_license_state"


freeze_time = "2019-05-05T12:00:00"


info = [
    ["license_state"],
    [
        "Splunk_Enterprise_Splunk_Analytics_for_Hadoop_Download_Trial",
        "5",
        "30",
        "524288000",
        "1561977130",
        "VALID",
    ],
    ["Splunk_Forwarder", "5", "30", "1048576", "2147483647", "VALID"],
    ["Splunk_Free", "3", "30", "524288000", "2147483647", "VALID"],
]


discovery = {
    "": [
        ("Splunk_Enterprise_Splunk_Analytics_for_Hadoop_Download_Trial", {}),
        ("Splunk_Forwarder", {}),
        ("Splunk_Free", {}),
    ]
}


checks = {
    "": [
        (
            "Splunk_Enterprise_Splunk_Analytics_for_Hadoop_Download_Trial",
            {"expiration_time": (1209600, 604800), "state": 2},
            [
                (0, "Status: VALID", []),
                (0, "Expiration time: 2019-07-01 12:32:10", []),
                (0, "Max violations: 5 within window period of 30 Days, Quota: 500 MiB", []),
            ],
        ),
        (
            "Splunk_Forwarder",
            {"expiration_time": (1209600, 604800), "state": 2},
            [
                (0, "Status: VALID", []),
                (0, "Expiration time: 2038-01-19 04:14:07", []),
                (0, "Max violations: 5 within window period of 30 Days, Quota: 1.00 MiB", []),
            ],
        ),
        (
            "Splunk_Free",
            {"expiration_time": (1209600, 604800), "state": 2},
            [
                (0, "Status: VALID", []),
                (0, "Expiration time: 2038-01-19 04:14:07", []),
                (0, "Max violations: 3 within window period of 30 Days, Quota: 500 MiB", []),
            ],
        ),
    ]
}
