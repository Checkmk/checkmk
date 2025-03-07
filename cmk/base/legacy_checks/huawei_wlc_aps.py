#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import NamedTuple

from cmk.base.check_legacy_includes.temperature import check_temperature

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import contains, render, SNMPTree

check_info = {}


class StateTemplate(NamedTuple):
    label: str
    value: int


radio_unknown = StateTemplate("not available", 3)
radio_state_map = {"1": StateTemplate("up", 0), "2": StateTemplate("down", 2)}

ap_unknown = StateTemplate("not available", 3)
ap_state_map = {
    "1": StateTemplate("Idle", 2),
    "2": StateTemplate("Auto find", 1),
    "3": StateTemplate("Type not match", 2),
    "4": StateTemplate("Fault", 2),
    "5": StateTemplate("Config", 2),
    "6": StateTemplate("Config failed", 2),
    "7": StateTemplate("Download", 1),
    "8": StateTemplate("Normal", 0),
    "9": StateTemplate("Committing", 2),
    "10": StateTemplate("Commit failed", 2),
    "11": StateTemplate("Standy", 1),
    "12": StateTemplate("Version mismatch", 2),
    "13": StateTemplate("Name conflicted", 2),
    "14": StateTemplate("Invalid", 2),
    "15": StateTemplate("Country code mismatch", 2),
}

# Defined by customer, see SUP-1020


def parse_huawei_wlc_aps(string_table):
    parsed = {}

    # Filter Access Point Information from Offline Access Points
    down_states = [key for key, value in ap_state_map.items() if value.value == 2]
    string_table[0] = [line for line in string_table[0] if line[0] not in down_states]

    aps_info1, aps_info2 = string_table

    # Access-Points
    for idx, ap_info1 in enumerate(aps_info1):
        # aps_info1 has general information about Access-point
        # aps_info2 has band information about Access-point
        # Every second line of aps_info1 matches aps_info2
        # aps_info1             aps_info2
        # [line]        -->     [2,4GHZ Info]
        #               -->     [5GHz Info]
        
        status, mem, cpu, temp, con_users = ap_info1
        ap_id, radio_state_2GHz, ch_usage_2GHz, users_online_2GHz = aps_info2[2 * idx]
        _ap_id, radio_state_5GHz, ch_usage_5GHz, users_online_5GHz = aps_info2[2 * idx + 1]

        if temp == "255":
            temp = "invalid"
        else:
            temp = float(temp)

        parsed[ap_id] = {
            "cmk_status": ap_state_map.get(status, ap_unknown).value,
            "state_readable": ap_state_map.get(status, ap_unknown).label,
            "mem_used_percent": float(mem),
            "cpu_percent": float(cpu),
            "temp": temp,
            "con_users": con_users,
            "24ghz": {
                "radio_cmk_state": radio_state_map.get(radio_state_2GHz, radio_unknown).value,
                "radio_readable_state": radio_state_map.get(radio_state_2GHz, radio_unknown).label,
                "ch_usage": float(ch_usage_2GHz),
                "users_online": int(users_online_2GHz),
            },
            "5ghz": {
                "radio_cmk_state": radio_state_map.get(radio_state_5GHz, radio_unknown).value,
                "radio_readable_state": radio_state_map.get(radio_state_5GHz, radio_unknown).label,
                "ch_usage": float(ch_usage_5GHz),
                "users_online": int(users_online_5GHz),
            },
        }

    return parsed


check_info["huawei_wlc_aps"] = LegacyCheckDefinition(
    name="huawei_wlc_aps",
    detect=contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.2011.2.240.17"),
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.2011.6.139.13.3.3.1",
            oids=["6", "40", "41", "43", "44"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.2011.6.139.16.1.2.1",
            oids=["3", "6", "25", "40"],
        ),
    ],
    parse_function=parse_huawei_wlc_aps,
)


def discovery_huawei_wlc_aps_status(parsed):
    for name, value in parsed.items():
        if value["state_readable"] is not None:
            yield name, {}


def check_huawei_wlc_aps_status(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    # General AP Status
    yield data["cmk_status"], "%s" % data["state_readable"]

    # AP Connected users
    yield 0, "Connected users: %s" % data["con_users"]

    # Band-dependent metrics
    for metric, band in (("24ghz", "2,4GHz"), ("5ghz", "5GHz")):
        # Number of users online
        users_online = data[metric]["users_online"]
        yield check_levels(
            users_online,
            "%s_clients" % metric,
            (None, None),
            human_readable_func=lambda x: "%d" % x,
            infoname="Users online [%s]" % band,
        )

        # Radio state
        radio_state = data[metric]["radio_cmk_state"]
        radio_readable = data[metric]["radio_readable_state"]
        yield radio_state, f"Radio state [{band}]: {radio_readable}"

        # Channel usage
        ch_usage = data[metric]["ch_usage"]
        ch_usage_lev = params["levels"]
        yield check_levels(
            ch_usage,
            "channel_utilization_%s" % metric,
            ch_usage_lev,
            human_readable_func=render.percent,
            infoname="Channel usage [%s]" % band,
        )


check_info["huawei_wlc_aps.status"] = LegacyCheckDefinition(
    name="huawei_wlc_aps_status",
    service_name="AP %s Status",
    sections=["huawei_wlc_aps"],
    discovery_function=discovery_huawei_wlc_aps_status,
    check_function=check_huawei_wlc_aps_status,
    check_default_parameters={"levels": (80.0, 90.0)},
)


def discovery_huawei_wlc_aps_cpu(parsed):
    for name, value in parsed.items():
        if value["cpu_percent"] is not None:
            yield name, {}


def check_huawei_wlc_aps_cpu(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    lev = params["levels"]
    val = data["cpu_percent"]
    yield check_levels(
        val, "cpu_percent", lev, human_readable_func=render.percent, infoname="Usage"
    )


check_info["huawei_wlc_aps.cpu"] = LegacyCheckDefinition(
    name="huawei_wlc_aps_cpu",
    service_name="AP %s CPU",
    sections=["huawei_wlc_aps"],
    discovery_function=discovery_huawei_wlc_aps_cpu,
    check_function=check_huawei_wlc_aps_cpu,
    check_default_parameters={"levels": (80.0, 90.0)},
)


def discovery_huawei_wlc_aps_mem(parsed):
    for name, value in parsed.items():
        if value["mem_used_percent"] is not None:
            yield name, {}


def check_huawei_wlc_aps_mem(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    lev = params["levels"]
    val = data["mem_used_percent"]
    yield check_levels(
        val,
        "mem_used_percent",
        lev,
        human_readable_func=render.percent,
        infoname="Used",
    )


check_info["huawei_wlc_aps.mem"] = LegacyCheckDefinition(
    name="huawei_wlc_aps_mem",
    service_name="AP %s Memory",
    sections=["huawei_wlc_aps"],
    discovery_function=discovery_huawei_wlc_aps_mem,
    check_function=check_huawei_wlc_aps_mem,
    check_default_parameters={"levels": (80.0, 90.0)},
)


def discovery_huawei_wlc_aps_temp(parsed):
    yield from ((name, {}) for name in parsed)


def check_huawei_wlc_aps_temp(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    # AP Temp
    temp = data["temp"]

    # "invalid" corresponds to 255 and should *not be* alaramed as per customer's requirements
    # See SUP-1020 for details
    if isinstance(temp, float):
        yield check_temperature(temp, {}, "AP %s Temperature" % item)
    else:
        yield 0, "%s" % temp


check_info["huawei_wlc_aps.temp"] = LegacyCheckDefinition(
    name="huawei_wlc_aps_temp",
    service_name="AP %s Temperature",
    sections=["huawei_wlc_aps"],
    discovery_function=discovery_huawei_wlc_aps_temp,
    check_function=check_huawei_wlc_aps_temp,
)
