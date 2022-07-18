#!/usr/bin/env python3
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.check_legacy_includes import dhcp_pools


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
        (
            1,
            "free: 23 leases (32.9%) (warn/crit below 42.0/10.0%)",
            [("free_dhcp_leases", 23, 29, 7, 0, 70)],
        ),
        (
            1,
            "used: 42 leases (60.0%) (warn/crit below 50/23 used pool entries)",
            [("used_dhcp_leases", 42, 50, 23, 0, 70)],
        ),
        (0, "5 leases pending", [("pending_dhcp_leases", 5, None, None, 0, 70)]),
    ]
