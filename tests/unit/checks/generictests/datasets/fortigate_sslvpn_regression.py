#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated
checkname = "fortigate_sslvpn"

info = [[["root"]], [["2", "9", "6", "6", "20"]]]

discovery = {"": [("root", {})]}

checks = {
    "": [
        (
            "root",
            {},
            [
                (0, "enabled", []),
                (0, "Users: 9", [("active_vpn_users", 9, None, None, None, None)]),
                (0, "Web sessions: 6", [("active_vpn_websessions", 6, None, None, None, None)]),
                (0, "Tunnels: 6", [("active_vpn_tunnels", 6, None, None, 0.0, 20.0)]),
            ],
        )
    ]
}
