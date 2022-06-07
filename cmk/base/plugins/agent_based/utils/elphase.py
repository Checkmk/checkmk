#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping, Optional, Tuple

from ..agent_based_api.v1 import check_levels, render, Result, State, type_defs

CheckParams = Optional[Mapping[str, Any]]
Sensor = Mapping[str, Any]
Section = Mapping[str, Sensor]


# Parsed has the following form:
# parsed = {
#    "Phase 1" : {
#        "device_state" : (1, "warning"),                 # overall device state: state, state readable
#        "voltage" : (220.17, (1, "Voltage is too low")), # with device state
#        "current" : 12.0,                                # without device state
#     }
# }
def check_elphase(  # pylint: disable=too-many-branches
    item: str,
    params: CheckParams,
    section: Section,
) -> type_defs.CheckResult:
    if item not in section:
        return  # Item not found in SNMP data

    class Bounds:
        Lower, Upper, Both = range(3)

    if params is None:
        params = {}

    if "device_state" in section[item]:
        device_state, device_state_readable = section[item]["device_state"]
        if "map_device_states" in params:
            device_state_params = dict(params["map_device_states"])
            if device_state in device_state_params:
                state = device_state_params[device_state]
            elif device_state_readable in device_state_params:
                state = device_state_params[device_state_readable]
            else:
                state = 0
        else:
            state = device_state
        yield Result(
            state=State(state),
            summary="Device status: %s(%s)" % (device_state_readable, device_state),
        )

    for quantity, title, render_func, bound, factor in [
        ("voltage", "Voltage", lambda x: f"{x:.1f} V", Bounds.Lower, 1),
        ("current", "Current", lambda x: f"{x:.1f} A", Bounds.Upper, 1),
        ("output_load", "Load", render.percent, Bounds.Upper, 1),
        ("power", "Power", lambda x: f"{x:.1f} W", Bounds.Upper, 1),
        ("appower", "Apparent Power", lambda x: f"{x:.1f} VA", Bounds.Upper, 1),
        ("energy", "Energy", lambda x: f"{x:.1f} Wh", Bounds.Upper, 1),
        ("frequency", "Frequency", lambda x: f"{x:.1f} hz", Bounds.Both, 1),
        (
            "differential_current_ac",
            "Differential current AC",
            lambda x: f"{(x * 1000):.1f} mA",
            Bounds.Upper,
            0.001,
        ),
        (
            "differential_current_dc",
            "Differential current DC",
            lambda x: f"{(x * 1000):.1f} mA",
            Bounds.Upper,
            0.001,
        ),
    ]:
        if quantity not in section[item]:
            continue

        entry = section[item][quantity]
        if isinstance(entry, tuple):
            value, state_info = entry  # (220.17, (1, "Voltage is too low"))
        else:
            value = entry  # 12.0
            state_info = None

        levels_upper: Optional[Tuple[float, float]] = None
        levels_lower: Optional[Tuple[float, float]] = None
        if quantity in params:
            if bound == Bounds.Both:
                levels = params[quantity]
                if levels[0] is not None and levels[1] is not None:
                    levels_upper = (factor * levels[0], factor * levels[1])
                if levels[2] is not None and levels[3] is not None:
                    levels_lower = (factor * levels[2], factor * levels[3])
            elif bound == Bounds.Upper:
                levels = params[quantity]
                if levels[0] is not None and levels[1] is not None:
                    levels_upper = (factor * levels[0], factor * levels[1])
            else:  # Bounds.Lower
                levels = params[quantity]
                if levels[0] is not None and levels[1] is not None:
                    levels_lower = (factor * levels[0], factor * levels[1])

        yield from check_levels(
            value * factor,
            levels_upper=levels_upper,
            levels_lower=levels_lower,
            metric_name=quantity,
            render_func=render_func,
            label=title,
        )

        if state_info:
            yield Result(state=State(state_info[0]), summary=state_info[1])
