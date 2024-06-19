#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from .checktestlib import Check


def test_fortigate_sslvpn_old_params() -> None:
    check = Check("fortigate_sslvpn")
    parsed = {
        "domain": {
            "state": "1",
            "users": 0,
            "web_sessions": 0,
            "tunnels": 0,
            "tunnels_max": 0,
        },
    }
    check.run_check("no-item", None, parsed)
