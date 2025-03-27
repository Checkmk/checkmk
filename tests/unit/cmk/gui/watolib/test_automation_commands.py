#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.watolib.automation_commands import AutomationPing


def test_parse_omd_status() -> None:
    # raw status tested in tests/integration/omd/test_omd.py
    raw_status = (
        "jaeger 5\n"
        "agent-receiver 0\n"
        "mkeventd 0\n"
        "liveproxyd 0\n"
        "mknotifyd 0\n"
        "rrdcached 0\n"
        "redis 0\n"
        "npcd 5"
    )

    assert AutomationPing()._parse_omd_status(raw_status=raw_status) == {
        "jaeger": 5,
        "agent-receiver": 0,
        "mkeventd": 0,
        "liveproxyd": 0,
        "mknotifyd": 0,
        "rrdcached": 0,
        "redis": 0,
        "npcd": 5,
    }, (
        "The function should return a dictionary "
        "with the service names as keys and their states as values"
    )
