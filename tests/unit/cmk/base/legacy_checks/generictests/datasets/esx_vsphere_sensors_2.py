#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code=var-annotated

checkname = "esx_vsphere_sensors"

info = [["Dummy sensor", "", "", "", "", "", "green", "all is good", "the sun is shining"]]

discovery = {"": [(None, {})]}

checks = {
    "": [
        (
            None,
            {"rules": []},
            [
                (
                    0,
                    (
                        "All sensors are in normal state\n"
                        "Sensors operating normal are:\n"
                        "Dummy sensor: all is good (the sun is shining)"
                    ),
                    [],
                )
            ],
        )
    ]
}
