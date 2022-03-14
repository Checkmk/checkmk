#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore
checkname = "fortigate_sslvpn"

info = [[["root"]], [["1", "0", "0", "0", "0"]]]

discovery = {"": [("root", {})]}

checks = {
    "": [
        (
            "root",
            None,
            [
                (0, "disabled", []),
                (0, "Users: 0", [("active_vpn_users", 0, None, None, None, None)]),
                (0, "Web sessions: 0", [("active_vpn_websessions", 0, None, None, None, None)]),
                (
                    0,
                    "Tunnels: 0",
                    [("active_vpn_tunnels", 0, None, None, 0, 0)],
                ),
            ],
        ),
    ]
}
