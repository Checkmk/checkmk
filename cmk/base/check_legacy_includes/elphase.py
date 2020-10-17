#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore[var-annotated,list-item,import,assignment,misc,operator]  # TODO: see which are needed in this file


def inventory_elphase(parsed):
    for item in parsed:
        yield item, {}


# Parsed has the following form:
# parsed = {
#    "Phase 1" : {
#        "device_state" : (1, "warning"),                 # overall device state: state, state readable
#        "voltage" : (220.17, (1, "Voltage is too low")), # with device state
#        "current" : 12.0,                                # without device state
#     }
# }
def check_elphase(item, params, parsed):
    if item not in parsed:
        return  # Item not found in SNMP data

    def tostring(value):
        if isinstance(value, int):
            return "%d" % value
        return "%.1f" % value

    class Bounds:
        Lower, Upper, Both = range(3)

    if params is None:
        params = {}

    if "device_state" in parsed[item]:
        device_state, device_state_readable = parsed[item]["device_state"]
        if params.get("map_device_states", []):
            device_state_params = dict(params["map_device_states"])
            if device_state in device_state_params:
                state = device_state_params[device_state]
            elif device_state_readable in device_state_params:
                state = device_state_params[device_state_readable]
            else:
                state = 0
        else:
            state = device_state
        yield state, "Device status: %s(%s)" % (device_state_readable, device_state)

    for what, title, unit, bound, factor in [
        ("voltage", "Voltage", " V", Bounds.Lower, 1),
        ("current", "Current", " A", Bounds.Upper, 1),
        ("output_load", "Load", "%", Bounds.Upper, 1),
        ("power", "Power", " W", Bounds.Upper, 1),
        ("appower", "Apparent Power", " VA", Bounds.Upper, 1),
        ("energy", "Energy", " Wh", Bounds.Upper, 1),
        ("frequency", "Frequency", " hz", Bounds.Both, 1),
        ("differential_current_ac", "Differential current AC", " mA", Bounds.Upper, 0.001),
        ("differential_current_dc", "Differential current DC", " mA", Bounds.Upper, 0.001),
    ]:

        if what in parsed[item]:
            entry = parsed[item][what]
            if isinstance(entry, tuple):
                value, state_info = entry  # (220.17, (1, "Voltage is too low"))
            else:
                value = entry  # 12.0
                state_info = None

            infotext = "%s: %s%s" % (title, tostring(value), unit)
            status = 0
            perfdata = [(what, value * factor)]

            if what in params:
                warn_lower = crit_lower = warn = crit = None
                if bound == Bounds.Both:
                    warn_lower, crit_lower, warn, crit = params[what]
                elif bound == Bounds.Upper:
                    warn, crit = params[what]
                else:  # Bounds.Lower
                    warn_lower, crit_lower = params[what]

                if warn_lower:
                    levelstext = " (warn/crit below %s/%s%s)" %\
                        (tostring(warn_lower), tostring(crit_lower), unit)
                    if value < crit_lower:
                        status = 2
                        infotext += levelstext
                    elif value < warn_lower:
                        status = max(status, 1)
                        infotext += levelstext

                if warn:
                    levelstext = " (warn/crit at %s/%s%s)" %\
                        (tostring(warn), tostring(crit), unit)
                    if value > crit:
                        status = 2
                        infotext += levelstext
                    elif value > warn:
                        status = max(status, 1)
                        infotext += levelstext

                    perfdata = [(what, value * factor, warn * factor, crit * factor)]

            yield status, infotext, perfdata

            if state_info:
                yield state_info
