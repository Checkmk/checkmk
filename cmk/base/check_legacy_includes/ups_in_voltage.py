#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=no-else-return


def check_ups_in_voltage(item, params, info):
    warn_lower, crit_lower = params["levels_lower"]
    warn_upper, crit_upper = params.get("levels_upper", (None, None))
    for line in info:
        if line[0] == item:
            power = int(line[1])
            perfdata = [
                (
                    "in_voltage",
                    power,
                    warn_upper if warn_upper is not None else warn_lower,
                    crit_upper if crit_upper is not None else crit_lower,
                    150,
                )
            ]
            infotext = "in voltage: %dV" % power
            lower_text = "(warn/crit below %sV/%sV)" % (warn_lower, crit_lower)
            upper_text = "(warn/crit at %sV/%sV)" % (warn_upper, crit_upper)

            if power <= crit_lower:
                return (2, "%s, %s" % (infotext, lower_text), perfdata)
            elif crit_upper is not None and power >= crit_upper:
                return (2, "%s, %s" % (infotext, upper_text), perfdata)
            elif power <= warn_lower:
                return (1, "%s, %s" % (infotext, lower_text), perfdata)
            elif warn_upper is not None and power >= warn_upper:
                return (1, "%s, %s" % (infotext, upper_text), perfdata)
            return (0, infotext, perfdata)

    return (3, "Phase %s not found in SNMP output" % item)
