#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="index"
# mypy: disable-error-code="no-untyped-def"

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import contains, SNMPTree, StringTable

check_info = {}

hp_sts_drvbox_type_map = {
    "1": "other",
    "2": "ProLiant Storage System",
    "3": "ProLiant-2 Storage System",
    "4": "internal ProLiant-2 Storage System",
    "5": "proLiant2DuplexTop",
    "6": "proLiant2DuplexBottom",
    "7": "proLiant2InternalDuplexTop",
    "8": "proLiant2InternalDuplexBottom",
}

hp_sts_drvbox_cond_map = {
    "1": (3, "other"),
    "2": (0, "ok"),
    "3": (1, "degraded"),
    "4": (2, "failed"),
}

hp_sts_drvbox_fan_map = {
    "1": (3, "other"),
    "2": (0, "ok"),
    "3": (2, "failed"),
    "4": (None, "noFan"),
    "5": (1, "degraded"),
}

hp_sts_drvbox_temp_map = {
    "1": (3, "other"),
    "2": (0, "ok"),
    "3": (1, "degraded"),
    "4": (2, "failed"),
    "5": (None, "noTemp"),
}

hp_sts_drvbox_sp_map = {
    "1": (3, "other"),
    "2": (0, "sidePanelInPlace"),
    "3": (2, "sidePanelRemoved"),
    "4": (None, "noSidePanelStatus"),
}

hp_sts_drvbox_power_map = {
    "1": (3, "other"),
    "2": (0, "ok"),
    "3": (1, "degraded"),
    "4": (2, "failed"),
    "5": (None, "noFltTolPower"),
}


def discover_hp_sts_drvbox(info):
    if info:
        return [
            (line[0] + "/" + line[1], None) for line in info if line[3] != ""
        ]  # only inventorize rows with "model" set
    return []


def check_hp_sts_drvbox(item, _no_params, info):
    for line in info:
        if line[0] + "/" + line[1] == item:
            (
                _c_index,
                _b_index,
                ty,
                model,
                fan_status,
                cond,
                temp_status,
                sp_status,
                pwr_status,
                serial,
                loc,
            ) = line

            sum_state = 0
            output = []

            for val, label, map_ in [
                (fan_status, "Fan-Status", hp_sts_drvbox_fan_map),
                (cond, "Condition", hp_sts_drvbox_cond_map),
                (temp_status, "Temp-Status", hp_sts_drvbox_temp_map),
                (sp_status, "Sidepanel-Status", hp_sts_drvbox_sp_map),
                (pwr_status, "Power-Status", hp_sts_drvbox_power_map),
            ]:
                this_state = map_[val][0]
                if this_state is None:
                    continue  # skip unsupported checks
                state_txt = ""
                if this_state == 1:
                    state_txt = " (!)"
                elif this_state == 2:
                    state_txt = " (!!)"
                sum_state = max(sum_state, this_state)
                output.append(f"{label}: {map_[val][1]}{state_txt}")

            output.append(
                "(Type: {}, Model: {}, Serial: {}, Location: {})".format(
                    hp_sts_drvbox_type_map.get(ty, "unknown"), model, serial, loc
                )
            )

            return (sum_state, ", ".join(output))
    return (3, "Controller not found in snmp data")


def parse_hp_sts_drvbox(string_table: StringTable) -> StringTable:
    return string_table


check_info["hp_sts_drvbox"] = LegacyCheckDefinition(
    name="hp_sts_drvbox",
    parse_function=parse_hp_sts_drvbox,
    detect=contains(".1.3.6.1.4.1.232.2.2.4.2.0", "proliant"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.232.8.2.1.1",
        oids=["1", "2", "3", "4", "7", "8", "9", "10", "11", "17", "23"],
    ),
    service_name="Drive Box %s",
    discovery_function=discover_hp_sts_drvbox,
    check_function=check_hp_sts_drvbox,
)
