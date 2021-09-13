#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore
checkname = "zorp_connections"

info = [
    ["Instance", "scb_ssh:", "walking"],
    ["zorp.stats.active_connections:", "0"],
    ["Instance", "scb_rdp:", "walking"],
    ["zorp.stats.active_connections:", "16"],
    ["Instance", "scb_telnet:", "walking"],
    ["zorp.stats.active_connections:", "None"],
    ["Instance", "scb_vnc:", "walking"],
    ["zorp.stats.active_connections:", "None"],
    ["Instance", "scb_ica:", "walking"],
    ["zorp.stats.active_connections:", "None"],
    ["Instance", "scb_http:", "walking"],
    ["zorp.stats.active_connections:", "None"],
]

discovery = {"": [(None, {})]}

checks = {
    "": [
        (
            None,
            {"levels": (16, 25)},
            [
                (0, "scb_ssh: 0", []),
                (0, "scb_rdp: 16", []),
                (0, "scb_telnet: 0", []),
                (0, "scb_vnc: 0", []),
                (0, "scb_ica: 0", []),
                (0, "scb_http: 0", []),
                (
                    1,
                    "Total connections: 16 (warn/crit at 16/25)",
                    [("connections", 16, 16.0, 25.0, None, None)],
                ),
            ],
        )
    ]
}
