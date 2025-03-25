#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


def check_ups_out_voltage(item, params, info):
    warn, crit = params["levels_lower"]
    for line in info:
        if line[0] == item:
            power = int(line[1])
            perfdata = [("out_voltage", power, warn, crit, 200, 240)]
            infotext = "out voltage: %dV (warn/crit at %dV/%dV)" % (power, warn, crit)

            if power <= crit:
                return (2, infotext, perfdata)
            elif power <= warn:
                return (1, infotext, perfdata)
            return (0, infotext, perfdata)

    return (3, "Phase %s not found in SNMP output" % item)
