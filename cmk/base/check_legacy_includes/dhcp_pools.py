#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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

    for what, value in [("free", free), ("used", used)]:
        state = 0
        value_abs = value

        if size == 0:
            value_perc = 0
        else:
            value_perc = float(value) / size * 100.0

        infotext = "%s: %d leases (%.1f%%)" % (what, value, value_perc)
        if params.get("%s_leases" % what, ""):
            warn, crit = params["%s_leases" % what]
            if isinstance(warn, float):  # here we have levels in percent
                value = value_perc
                text_format = "%.1f"
                unit = "%%"
                warn_abs = int(size * (warn / 100.0))
                crit_abs = int(size * (crit / 100.0))
            else:  # otherwise we use absolute values as integers
                text_format = "%d"
                unit = " %s pool entries" % what
                warn_abs = warn
                crit_abs = crit

            if value < crit:
                state = 2
            elif value < warn:
                state = 1

            if state:
                infotext_format = (
                    " (warn/crit below " + text_format + "/" + text_format + unit + ")"
                )
                infotext += infotext_format % (warn, crit)

        else:
            warn_abs = None
            crit_abs = None

        yield state, infotext, [("%s_dhcp_leases" % what, value_abs, warn_abs, crit_abs, 0, size)]

    if pending is not None:
        yield 0, "%d leases pending" % pending, [
            ("pending_dhcp_leases", pending, None, None, 0, size)
        ]
