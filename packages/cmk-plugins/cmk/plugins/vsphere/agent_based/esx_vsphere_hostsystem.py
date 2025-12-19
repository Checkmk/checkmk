#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from cmk.agent_based.legacy.v0_unstable import STATE_MARKERS
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
)
from cmk.plugins.vsphere.agent_based.esx_vsphere_hostsystem_section import HostSystemSection

# .
#   .--State---------------------------------------------------------------.
#   |                       ____  _        _                               |
#   |                      / ___|| |_ __ _| |_ ___                         |
#   |                      \___ \| __/ _` | __/ _ \                        |
#   |                       ___) | || (_| | ||  __/                        |
#   |                      |____/ \__\__,_|\__\___|                        |
#   |                                                                      |
#   +----------------------------------------------------------------------+


def discover_esx_vsphere_hostsystem_state(section: HostSystemSection) -> DiscoveryResult:
    if "runtime.inMaintenanceMode" in section:
        yield Service()


def check_esx_vsphere_hostsystem_state(section: HostSystemSection) -> CheckResult:
    state = State.OK
    if "overallStatus" not in section:
        return

    overallStatus = str(section["overallStatus"][0])
    if overallStatus == "yellow":
        state = State.WARN
    elif overallStatus in ["red", "gray"]:
        state = State.CRIT
    yield Result(state=state, summary=f"Entity state: {overallStatus}")

    state = State.OK
    powerState = str(section["runtime.powerState"][0])
    if powerState in ["poweredOff", "unknown"]:
        state = State.CRIT
    elif powerState == "standBy":
        state = State.WARN
    yield Result(state=state, summary=f"Power state: {powerState}")


check_plugin_esx_vsphere_hostsystem_state = CheckPlugin(
    name="esx_vsphere_hostsystem_state",
    service_name="Overall state",
    sections=["esx_vsphere_hostsystem"],
    discovery_function=discover_esx_vsphere_hostsystem_state,
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


def discover_esx_vsphere_hostsystem_maintenance(section: HostSystemSection) -> DiscoveryResult:
    if "runtime.inMaintenanceMode" in section:
        current_state = str(section["runtime.inMaintenanceMode"][0]).lower()
        yield Service(parameters={"target_state": current_state})


def check_esx_vsphere_hostsystem_maintenance(
    params: Mapping[str, Any], section: HostSystemSection
) -> CheckResult:
    target_state = params["target_state"]

    if "runtime.inMaintenanceMode" not in section:
        return None

    current_state = str(section["runtime.inMaintenanceMode"][0]).lower()
    state = State.OK
    if target_state != current_state:
        state = State.CRIT
    if current_state == "true":
        yield Result(state=state, summary="System running is in Maintenance mode")
        return
    yield Result(state=state, summary="System not in Maintenance mode")
    return


check_plugin_esx_vsphere_hostsystem_maintenance = CheckPlugin(
    name="esx_vsphere_hostsystem_maintenance",
    service_name="Maintenance Mode",
    sections=["esx_vsphere_hostsystem"],
    discovery_function=discover_esx_vsphere_hostsystem_maintenance,
    check_function=check_esx_vsphere_hostsystem_maintenance,
    check_default_parameters={},
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


def esx_vsphere_multipath_convert(data: HostSystemSection) -> Mapping[str, list[tuple[str, str]]]:
    raw_path_info = data.get("config.storageDevice.multipathInfo")
    if not raw_path_info:
        return {}

    paths = dict[str, list[tuple[str, str]]]()
    for lun_id, path, state in zip(raw_path_info[::3], raw_path_info[1::3], raw_path_info[2::3]):
        paths.setdefault(lun_id, []).append((state, path))
    return paths


def discover_esx_vsphere_hostsystem_multipath(section: HostSystemSection) -> DiscoveryResult:
    yield from [Service(item=x) for x in esx_vsphere_multipath_convert(section)]


@dataclass
class StateInfo:
    alert_state: int
    count: int
    info: str


def check_esx_vsphere_hostsystem_multipath(
    item: str,
    params: Mapping[str, Any],
    section: HostSystemSection,
) -> CheckResult:
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

    if not (states := esx_vsphere_multipath_convert(section).get(item)):
        return

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

    yield Result(state=State(state), summary=message.split("\n")[0], details=message)


check_plugin_esx_vsphere_hostsystem_multipath = CheckPlugin(
    name="esx_vsphere_hostsystem_multipath",
    service_name="Multipath %s",
    sections=["esx_vsphere_hostsystem"],
    discovery_function=discover_esx_vsphere_hostsystem_multipath,
    check_function=check_esx_vsphere_hostsystem_multipath,
    check_ruleset_name="multipath_count",
    check_default_parameters={"levels_map": None},
)
