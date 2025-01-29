#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Mapping

from cmk.agent_based.v2 import Metric, Result
from cmk.plugins.lib import dhcp_pools

# new params format
# params = {
#    'free_leases' : (warn, crit),
#    'used_leases' : (warn, crit),
# }


def check_dhcp_pools_levels(
    free: float | None,
    used: float | None,
    pending: float | None,
    size: float,
    params: Mapping[str, tuple[float, float]],
) -> Iterable[tuple[int, str, list]]:
    for new_api_object in dhcp_pools.check_dhcp_pools_levels(free, used, pending, size, params):
        if isinstance(new_api_object, Result):
            yield int(new_api_object.state), new_api_object.summary, []
        if isinstance(new_api_object, Metric):
            yield (
                0,
                "",
                [
                    (
                        new_api_object.name,
                        new_api_object.value,
                        *new_api_object.levels,
                        *new_api_object.boundaries,
                    )
                ],
            )
