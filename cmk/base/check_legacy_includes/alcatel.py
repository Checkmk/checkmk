#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable

alcatel_cpu_default_levels = (90.0, 95.0)

ALCATEL_TEMP_CHECK_DEFAULT_PARAMETERS = {
    "levels": (45.0, 50.0),
}

DiscoveryResult = (
    Iterable[tuple[None, str | None]]
    | Iterable[tuple[str, str | None]]
    | Iterable[tuple[str, dict]]
)


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


def inventory_alcatel_cpu(info) -> DiscoveryResult:  # type:ignore[no-untyped-def]
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
        levelstext = f" (warn/crit at {warn:.1f}%/{crit:.1f}%)"
    perfdata = [("util", cpu_perc, warn, crit, 0, 100)]
    return status, "total: %.1f%%" % cpu_perc + levelstext, perfdata


def inventory_alcatel_fans(info) -> DiscoveryResult:  # type:ignore[no-untyped-def]
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
        return None

    state = 0 if fan_state == 2 else 2
    return state, "Fan " + fan_states.get(fan_state, "unknown (%s)" % fan_state)


def inventory_alcatel_temp(info) -> DiscoveryResult:  # type:ignore[no-untyped-def]
    with_slot = len(info) != 1
    for index, row in enumerate(info):
        for oid, name in enumerate(["Board", "CPU"]):
            if row[oid] != "0":
                if with_slot:
                    yield f"Slot {index + 1} {name}", {}
                else:
                    yield name, {}
