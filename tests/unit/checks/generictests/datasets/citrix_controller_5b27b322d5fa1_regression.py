#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# type: ignore


checkname = "citrix_controller"


info = [
    ["ControllerState"],
    ["ControllerVersion"],
    ["DesktopsRegistered"],
    ["LicensingServerState"],
    ["LicensingGraceState"],
    ["ActiveSiteServices"],
    ["TotalFarmActiveSessions", "0"],
    ["TotalFarmInactiveSessions", "0"],
]


discovery = {
    "": [(None, None)],
    "licensing": [(None, None)],
    "registered": [(None, None)],
    "services": [(None, None)],
    "sessions": [(None, {})],
}


checks = {
    "": [(None, {}, [(3, "unknown", [])])],
    "licensing": [(None, {}, [])],
    "registered": [(None, {}, [(3, "No desktops registered", [])])],
    "services": [(None, {}, [(0, "", [])])],
    "sessions": [
        (
            None,
            {},
            [
                (
                    0,
                    "total: 0, active: 0, inactive: 0",
                    [
                        ("total_sessions", 0, None, None, None, None),
                        ("active_sessions", 0, None, None, None, None),
                        ("inactive_sessions", 0, None, None, None, None),
                    ],
                )
            ],
        )
    ],
}
