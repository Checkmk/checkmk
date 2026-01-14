#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.base.check_legacy_includes.perle import perle_check_alarms

check_info = {}


def discover_perle_chassis_slots(info):
    return [
        (index, None)
        for index, _name, _modelname, _serial, _bootloader, _fw, _alarms_str, _diagstate, ty, _descr in info
        if ty != "0"
    ]


def check_perle_chassis_slots(item, _no_params, info):
    map_diagstates = {
        "0": (0, "passed"),
        "1": (2, "media converter module's PHY is not functional"),
        "2": (1, "firmware download required"),
    }

    for (
        index,
        name,
        _modelname,
        _serial,
        _bootloader,
        _fw,
        alarms_str,
        diagstate,
        _ty,
        _descr,
    ) in info:
        if item == index:
            state, state_readable = map_diagstates[diagstate]
            yield state, f"[{name}] Diagnostic result: {state_readable}"
            yield perle_check_alarms(alarms_str)


check_info["perle_chassis_slots"] = LegacyCheckDefinition(
    name="perle_chassis_slots",
    # section is already migrated!
    service_name="Chassis status slot %s",
    discovery_function=discover_perle_chassis_slots,
    check_function=check_perle_chassis_slots,
)
