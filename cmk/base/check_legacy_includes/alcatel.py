#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Iterable, Optional, Tuple, Union

from .temperature import check_temperature  # type: ignore[attr-defined]  # what's wrong?

alcatel_cpu_default_levels = (90.0, 95.0)

ALCATEL_TEMP_CHECK_DEFAULT_PARAMETERS = {
    "levels": (45, 50),
}

DiscoveryResult = Union[Iterable[Tuple[None, Optional[str]]], Iterable[Tuple[str, Optional[str]]]]


def alcatel_networking_products_scan_function(oid):
    """
    Devices running until AOS6 (including).
    """
    return oid(".1.3.6.1.2.1.1.2.0").startswith(  # MIB object "sysObjectID"
        ".1.3.6.1.4.1.6486.800"
    )  # MIB object "alcatelIND1BaseMIB"


def alcatel_new_networking_products_scan_function(oid):
    """
    Devices running at least AOS7 (including).
    Refer to alcatelENT1BaseMIB for more information.
    """
    return oid(".1.3.6.1.2.1.1.2.0").startswith(  # MIB object "sysObjectID"
        ".1.3.6.1.4.1.6486.801"
    )  # MIB object "alcatelENT1BaseMIB"


def inventory_alcatel_cpu(info) -> DiscoveryResult:
    return [(None, "alcatel_cpu_default_levels")]


def check_alcatel_cpu(_no_item, params, info):
    cpu_perc = int(info[0][0])
    warn, crit = params
    status = 0
    levelstext = ""
    if cpu_perc >= crit:
        status = 2
    elif cpu_perc >= warn:
        status = 1
    if status:
        levelstext = " (warn/crit at %.1f%%/%.1f%%)" % (warn, crit)
    perfdata = [("util", cpu_perc, warn, crit, 0, 100)]
    return status, "total: %.1f%%" % cpu_perc + levelstext, perfdata


def inventory_alcatel_fans(info) -> DiscoveryResult:
    for nr, _value in enumerate(info, 1):
        yield str(nr), None


def check_alcatel_fans(item, _no_params, info):
    fan_states = {
        0: "has no status",
        1: "not running",
        2: "running",
    }
    try:
        line = info[int(item) - 1]
        fan_state = int(line[0])
    except (ValueError, IndexError):
        return

    state = 0 if fan_state == 2 else 2
    return state, "Fan " + fan_states.get(fan_state, "unknown (%s)" % fan_state)


def inventory_alcatel_temp(info) -> DiscoveryResult:
    with_slot = len(info) != 1
    for index, row in enumerate(info):
        for oid, name in enumerate(["Board", "CPU"]):
            if row[oid] != "0":
                if with_slot:
                    yield "Slot %s %s" % (index + 1, name), {}
                else:
                    yield name, {}


def check_alcatel_temp(item, params, info):
    if len(info) == 1:
        slot_index = 0
    else:
        slot = int(item.split()[1])
        slot_index = slot - 1
    sensor = item.split()[-1]
    items = {"Board": 0, "CPU": 1}
    try:
        # If multiple switches are staked and one of them are
        # not reachable, prevent a exception
        temp_celsius = int(info[slot_index][items[sensor]])
    except Exception:
        return 3, "Sensor not found"
    return check_temperature(temp_celsius, params, "alcatel_temp_%s" % item)
