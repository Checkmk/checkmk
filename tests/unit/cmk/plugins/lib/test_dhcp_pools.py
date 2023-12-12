#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import Metric, Result, State
from cmk.plugins.lib import dhcp_pools


def test_check_dhcp_pools_levels() -> None:
    assert list(
        dhcp_pools.check_dhcp_pools_levels(
            free=23,
            used=42,
            pending=5,
            size=70,
            params={"free_leases": (42.0, 10.0), "used_leases": (50, 23)},
        )
    ) == [
        Result(state=State.OK, summary="Free leases: 23"),
        Result(state=State.WARN, summary="32.86% (warn/crit below 42.00%/10.00%)"),
        Metric("free_dhcp_leases", 23, levels=(29.4, 7.0), boundaries=(0, 70)),
        Result(state=State.WARN, summary="Used leases: 42 (warn/crit below 50/23)"),
        Result(state=State.OK, summary="60.00%"),
        Metric("used_dhcp_leases", 42, levels=(50, 23), boundaries=(0, 70)),
        Result(state=State.OK, summary="Pending leases: 5"),
        Result(state=State.OK, summary="7.14%"),
        Metric("pending_dhcp_leases", 5, boundaries=(0, 70)),
    ]
