#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# type: ignore[attr-defined]  # TODO: see which are needed in this file

from cmk.base.check_api import check_levels, get_percent_human_readable

_RENDER_FUNCTION_AND_UNIT = {
    "%": (
        get_percent_human_readable,
        "",
    ),
    "mA": (
        lambda current: f"{(current * 1000):.1f}",
        "mA",
    ),
}


# Parsed has the following form:
# parsed = {
#    "Phase 1" : {
#        "device_state" : (1, "warning"),                 # overall device state: state, state readable
#        "voltage" : (220.17, (1, "Voltage is too low")), # with device state
#        "current" : 12.0,                                # without device state
#     }
# }
# ==================================================================================================
# ==================================================================================================
# THIS FUNCTION HAS BEEN MIGRATED TO THE NEW CHECK API (OR IS IN THE PROCESS), PLEASE DO NOT TOUCH
# IT. INSTEAD, MODIFY THE MIGRATED VERSION.
# ==================================================================================================
# ==================================================================================================
def check_elphase(item, params, parsed):  # pylint: disable=too-many-branches
    if item not in parsed:
        return  # Item not found in SNMP data

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
        ("voltage", "Voltage", "V", Bounds.Lower, 1),
        ("current", "Current", "A", Bounds.Upper, 1),
        ("output_load", "Load", "%", Bounds.Upper, 1),
        ("power", "Power", "W", Bounds.Upper, 1),
        ("appower", "Apparent Power", "VA", Bounds.Upper, 1),
        ("energy", "Energy", "Wh", Bounds.Upper, 1),
        ("frequency", "Frequency", "hz", Bounds.Both, 1),
        ("differential_current_ac", "Differential current AC", "mA", Bounds.Upper, 0.001),
        ("differential_current_dc", "Differential current DC", "mA", Bounds.Upper, 0.001),
    ]:

        if what in parsed[item]:
            entry = parsed[item][what]
            if isinstance(entry, tuple):
                value, state_info = entry  # (220.17, (1, "Voltage is too low"))
            else:
                value = entry  # 12.0
                state_info = None

            levels = [None] * 4
            if what in params:
                if bound == Bounds.Both:
                    levels = params[what]
                elif bound == Bounds.Upper:
                    levels[:2] = params[what]
                else:  # Bounds.Lower
                    levels[2:] = params[what]

            render_func, unit = _RENDER_FUNCTION_AND_UNIT.get(
                unit,
                (
                    lambda v: f"{v:.1f}",
                    unit,
                ),
            )

            yield check_levels(
                value * factor,
                what,
                tuple(level if level is None else level * factor for level in levels),
                unit=unit,
                human_readable_func=render_func,
                infoname=title,
            )

            if state_info:
                yield state_info
