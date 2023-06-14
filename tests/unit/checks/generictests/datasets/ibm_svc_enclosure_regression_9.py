#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "ibm_svc_enclosure"


info = [["0", "online", "control", "9843-AE2", "6860407", "2", "2", "2", "12"]]


discovery = {"": [("0", {})]}


checks = {
    "": [
        (
            "0",
            {},
            [
                (0, "Status: online", []),
                (0, "Online canisters: 2 of 2", []),
                (0, "Online PSUs: 2", []),
            ],
        )
    ]
}
