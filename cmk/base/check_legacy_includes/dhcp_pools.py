#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.check_api import check_levels, get_percent_human_readable

# new params format
# params = {
#    'free_leases' : (warn, crit),
#    'used_leases' : (warn, crit),
# }


def check_dhcp_pools_levels(free, used, pending, size, params):
    if isinstance(params, tuple):
        # In case of win_dhcp_pools old params are percent but of type
        # integer, thus we have to change them into floats
        params = {"free_leases": (float(params[0]), float(params[1]))}

    for what, value in [("free", free), ("used", used), ("pending", pending)]:
        if value is None:
            continue

        value_abs = value
        value_perc = float(value) / size * 100.0 if size else 0.0

        levels_abs: tuple[float | None, float | None] = None, None
        levels_perc: tuple[float | None, float | None] = None, None
        metric_levels: tuple[float | None, float | None] = None, None
        if (levels := params.get("%s_leases" % what)) is not None:
            if isinstance(levels[0], float):  # here we have levels in percent
                levels_perc = levels
                metric_levels = levels[0] / 100.0 * size, levels[1] / 100.0 * size
            else:
                levels_abs = levels
                metric_levels = levels

        yield check_levels(
            value=value_abs,
            dsname=None,
            params=(None, None) + levels_abs,
            human_readable_func=lambda x: str(int(x)),
            infoname=f"{what.capitalize()} leases",
        )
        yield check_levels(
            value=value_perc,
            dsname=None,
            params=(None, None) + levels_perc,
            human_readable_func=get_percent_human_readable,
            infoname="",
        )
        yield 0, "", [("%s_dhcp_leases" % what, value_abs, *metric_levels, 0, size)]
