#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore[var-annotated,list-item,import,assignment,misc,operator]  # TODO: see which are needed in this file
# parsed = {
#     "Summary" : (13, ""),
#     "NAME 1"  : (5, INTERFACE),
#     "NAME 2"  : (8, INTERFACE),
# }


def inventory_wlc_clients(parsed):
    return [(name, {}) for name in parsed]


def check_wlc_clients(item, params, parsed):
    if isinstance(params, tuple):
        params = {
            "levels_lower": (params[1], params[0]),
            "levels": (params[2], params[3]),
        }

    if item in parsed:
        num_conns, interface = parsed[item]
        state = 0
        infotext = "%d connections" % num_conns
        perfdata = [("connections", num_conns)]
        if interface:
            infotext += " (%s)" % interface
        if params:
            if params.get("levels", None):
                warn, crit = params["levels"]
                levelstext = "at %d/%d" % (warn, crit)
                if num_conns >= crit:
                    state = 2
                elif num_conns >= warn:
                    state = 1

                perfdata = [("connections", num_conns, warn, crit)]

            elif params.get("levels_lower", None):
                warn_low, crit_low = params["levels_lower"]
                levelstext = "below %d/%d" % (warn_low, crit_low)
                if num_conns < crit_low:
                    state = 2
                elif num_conns < warn_low:
                    state = 1

            if state > 0:
                infotext += " (warn/crit %s)" % levelstext

        return state, infotext, perfdata
