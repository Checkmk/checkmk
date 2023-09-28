#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated
checkname = "checkpoint_packets"

mock_item_state = {
    "": {
        "accepted": (1572247078.0, 0),
        "rejected": (1572247078.0, 0),
        "dropped": (1572247078.0, 0),
        "logged": (1572247078.0, 0),
    },
}

info = [[["120", "180", "210", "4"]], []]

discovery = {"": [(None, {})]}

checks = {
    "": [
        (
            None,
            {
                "accepted": (100000, 200000),
                "rejected": (100000, 200000),
                "dropped": (100000, 200000),
                "logged": (100000, 200000),
                "espencrypted": (100000, 200000),
                "espdecrypted": (100000, 200000),
            },
            [
                (0, "Accepted: 2.0 pkts/s", [("accepted", 2.0, 100000, 200000, 0, None)]),
                (0, "Rejected: 3.0 pkts/s", [("rejected", 3.0, 100000, 200000, 0, None)]),
                (0, "Dropped: 3.5 pkts/s", [("dropped", 3.5, 100000, 200000, 0, None)]),
                (0, "Logged: 0.1 pkts/s", [("logged", 0.06666666666666666, 100000, 200000, 0, None)]),
            ],
        )
    ]
}
