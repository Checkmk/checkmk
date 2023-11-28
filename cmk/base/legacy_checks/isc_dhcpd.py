#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated,index,attr-defined"

from collections.abc import Mapping
from typing import Any, Iterator

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.dhcp_pools import check_dhcp_pools_levels
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.isc_dhcpd import DhcpdSection

# Example output from agent:
# <<<isc_dhcpd>>>
# [general]
# PID: 3670
# [pools]
# 10.0.1.1 10.0.1.254
# [leases]
# 10.0.1.16
# 10.0.1.24
# 10.0.1.26
# 10.0.1.27
# 10.0.1.34
# 10.0.1.36
# 10.0.1.45
# 10.0.1.50
# 10.0.1.53
# 10.0.1.57


def inventory_isc_dhcpd(parsed: DhcpdSection) -> Iterator[Any]:
    yield from ((item, None) for item in parsed.pools)


def check_isc_dhcpd(item: str, params: Mapping, parsed: DhcpdSection) -> Iterator[Any]:
    if not parsed.pids:
        yield 2, "DHCP Daemon not running"
    elif len(parsed.pids) > 1:
        yield 1, "DHCP Daemon running %d times (PIDs: %s)" % (
            len(parsed.pids),
            ", ".join(map(str, parsed.pids)),
        )

    if item not in parsed.pools:
        return

    ip_range = parsed.pools[item]
    num_leases = int(ip_range.end) - int(ip_range.start) + 1
    num_used = len(
        [lease_dec for lease_dec in parsed.leases if ip_range.start <= lease_dec <= ip_range.end]
    )

    yield from check_dhcp_pools_levels(num_leases - num_used, num_used, None, num_leases, params)


check_info["isc_dhcpd"] = LegacyCheckDefinition(
    service_name="DHCP Pool %s",
    discovery_function=inventory_isc_dhcpd,
    check_function=check_isc_dhcpd,
    check_ruleset_name="win_dhcp_pools",
    check_default_parameters={"free_leases": (15.0, 5.0)},
)
