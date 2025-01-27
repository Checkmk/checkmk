#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated"

from dataclasses import dataclass

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition, STATE_MARKERS

check_info = {}

# .
#   .--State---------------------------------------------------------------.
#   |                       ____  _        _                               |
#   |                      / ___|| |_ __ _| |_ ___                         |
#   |                      \___ \| __/ _` | __/ _ \                        |
#   |                       ___) | || (_| | ||  __/                        |
#   |                      |____/ \__\__,_|\__\___|                        |
#   |                                                                      |
#   +----------------------------------------------------------------------+


def inventory_esx_vsphere_hostsystem_state(parsed):
    if "runtime.inMaintenanceMode" in parsed:
        return [(None, None)]
    return []


def check_esx_vsphere_hostsystem_state(_no_item, _no_params, parsed):
    state = 0
    if "overallStatus" not in parsed:
        return

    overallStatus = str(parsed["overallStatus"][0])
    if overallStatus == "yellow":
        state = 1
    elif overallStatus in ["red", "gray"]:
        state = 2
    yield state, "Entity state: " + overallStatus

    state = 0
    powerState = str(parsed["runtime.powerState"][0])
    if powerState in ["poweredOff", "unknown"]:
        state = 2
    elif powerState == "standBy":
        state = 1
    yield state, "Power state: " + powerState


check_info["esx_vsphere_hostsystem.state"] = LegacyCheckDefinition(
    name="esx_vsphere_hostsystem_state",
    service_name="Overall state",
    sections=["esx_vsphere_hostsystem"],
    discovery_function=inventory_esx_vsphere_hostsystem_state,
    check_function=check_esx_vsphere_hostsystem_state,
)

# .
#   .--Maintenance---------------------------------------------------------.
#   |       __  __       _       _                                         |
#   |      |  \/  | __ _(_)_ __ | |_ ___ _ __   __ _ _ __   ___ ___        |
#   |      | |\/| |/ _` | | '_ \| __/ _ \ '_ \ / _` | '_ \ / __/ _ \       |
#   |      | |  | | (_| | | | | | ||  __/ | | | (_| | | | | (_|  __/       |
#   |      |_|  |_|\__,_|_|_| |_|\__\___|_| |_|\__,_|_| |_|\___\___|       |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   '----------------------------------------------------------------------'


def inventory_esx_vsphere_hostsystem_maintenance(parsed):
    if "runtime.inMaintenanceMode" in parsed:
        current_state = str(parsed["runtime.inMaintenanceMode"][0]).lower()
        return [(None, {"target_state": current_state})]
    return []


def check_esx_vsphere_hostsystem_maintenance(_no_item, params, parsed):
    target_state = params["target_state"]

    if "runtime.inMaintenanceMode" not in parsed:
        return None

    current_state = str(parsed["runtime.inMaintenanceMode"][0]).lower()
    state = 0
    if target_state != current_state:
        state = 2
    if current_state == "true":
        return state, "System running is in Maintenance mode"
    return state, "System not in Maintenance mode"


check_info["esx_vsphere_hostsystem.maintenance"] = LegacyCheckDefinition(
    name="esx_vsphere_hostsystem_maintenance",
    service_name="Maintenance Mode",
    sections=["esx_vsphere_hostsystem"],
    discovery_function=inventory_esx_vsphere_hostsystem_maintenance,
    check_function=check_esx_vsphere_hostsystem_maintenance,
    check_ruleset_name="esx_hostystem_maintenance",
)

# .
#   .--Multipath-----------------------------------------------------------.
#   |             __  __       _ _   _             _   _                   |
#   |            |  \/  |_   _| | |_(_)_ __   __ _| |_| |__                |
#   |            | |\/| | | | | | __| | '_ \ / _` | __| '_ \               |
#   |            | |  | | |_| | | |_| | |_) | (_| | |_| | | |              |
#   |            |_|  |_|\__,_|_|\__|_| .__/ \__,_|\__|_| |_|              |
#   |                                 |_|                                  |
#   +----------------------------------------------------------------------+

# 5.1
# fc.20000024ff2e1b4c:21000024ff2e1b4c-fc.500a098088866d7e:500a098188866d7e-naa.60a9800044314f68553f436779684544 active
# unknown.vmhba0-unknown.2:0-naa.6b8ca3a0facdc9001a2a27f8197dd718 active
# 5.5
# fc.20000024ff3708ec:21000024ff3708ec-fc.500a098088866d7e:500a098188866d7e-naa.60a9800044314f68553f436779684544 active
# fc.500143802425a24d:500143802425a24c-fc.5001438024483280:5001438024483288-naa.5001438024483280 active
# >= version 6.0
# vmhba32:C0:T0:L0 active


def esx_vsphere_multipath_convert(data):
    raw_path_info = data.get("config.storageDevice.multipathInfo")
    if not raw_path_info:
        return {}

    paths = {}
    for lun_id, path, state in zip(raw_path_info[::3], raw_path_info[1::3], raw_path_info[2::3]):
        paths.setdefault(lun_id, []).append((state, path))
    return paths


def inventory_esx_vsphere_hostsystem_multipath(parsed):
    return [(x, {}) for x in esx_vsphere_multipath_convert(parsed)]


@dataclass
class StateInfo:
    alert_state: int
    count: int
    info: str


def check_esx_vsphere_hostsystem_multipath(
    item,
    params,
    parsed,
):
    state_infos = {
        "active": StateInfo(0, 0, ""),
        "dead": StateInfo(2, 0, ""),
        "disabled": StateInfo(1, 0, ""),
        "standby": StateInfo(0, 0, ""),
        "unknown": StateInfo(2, 0, ""),
    }

    state = 0
    message = ""
    path_names = []

    states = esx_vsphere_multipath_convert(parsed).get(item)
    if states is None:
        return states

    levels_map = params["levels_map"]

    # Collect states
    for path_state, path_name in states:
        state_item = state_infos.get(path_state)
        path_info = path_name
        if state_item:
            state_item.count += 1
            state = max(state_item.alert_state, state)
            path_info += STATE_MARKERS[state_item.alert_state]
        path_names.append(path_info)

    # Check warn, critical
    if not levels_map or isinstance(levels_map, list):
        if (
            state_infos["standby"].count > 0
            and state_infos["standby"].count != state_infos["active"].count
        ):
            state = max(state_infos["standby"].alert_state, state)
    else:
        state = 0
        for state_name, state_values in state_infos.items():
            if levels_map.get(state_name):
                limits = levels_map.get(state_name)
                if len(limits) == 2:
                    warn_max, crit_max = limits
                    crit_min, warn_min = 0, 0
                else:
                    crit_min, warn_min, warn_max, crit_max = limits

                if state_values.count < crit_min:
                    state = max(state, 2)
                    state_values.info = "(!!)(less than %d)" % crit_min
                elif state_values.count > crit_max:
                    state = max(state, 2)
                    state_values.info = "(!!)(more than %d)" % crit_max
                elif state_values.count < warn_min:
                    state = max(state, 1)
                    state_values.info = "(!)(less than %d)" % warn_min
                elif state_values.count > warn_max:
                    state = max(state, 1)
                    state_values.info = "(!)(more than %d)" % warn_max

    # Output message
    message = ""

    element_text = []
    for element in "active", "dead", "disabled", "standby", "unknown":
        element_text.append(
            "%d %s%s" % (state_infos[element].count, element, state_infos[element].info)
        )
    message += ", ".join(element_text)
    message += "\nIncluded Paths:\n" + "\n".join(path_names)

    return state, message


check_info["esx_vsphere_hostsystem.multipath"] = LegacyCheckDefinition(
    name="esx_vsphere_hostsystem_multipath",
    service_name="Multipath %s",
    sections=["esx_vsphere_hostsystem"],
    discovery_function=inventory_esx_vsphere_hostsystem_multipath,
    check_function=check_esx_vsphere_hostsystem_multipath,
    check_ruleset_name="multipath_count",
    check_default_parameters={"levels_map": None},
)
