#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# Defined by customer, see SUP-1020

from collections.abc import Mapping, Sequence
from typing import NamedTuple, TypedDict

from cmk.agent_based.v1 import check_levels
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    get_value_store,
    render,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.temperature import check_temperature, TempParamType


class StateTemplate(NamedTuple):
    label: str
    value: State


_RADIO_UNKNOWN = StateTemplate("not available", State.UNKNOWN)
_RADIO_STATE_MAP = {"1": StateTemplate("up", State.OK), "2": StateTemplate("down", State.CRIT)}

_AP_UNKNOWN = StateTemplate("not available", State.UNKNOWN)
_AP_STATE_MAP = {
    "1": StateTemplate("Idle", State.CRIT),
    "2": StateTemplate("Auto find", State.WARN),
    "3": StateTemplate("Type not match", State.CRIT),
    "4": StateTemplate("Fault", State.CRIT),
    "5": StateTemplate("Config", State.CRIT),
    "6": StateTemplate("Config failed", State.CRIT),
    "7": StateTemplate("Download", State.WARN),
    "8": StateTemplate("Normal", State.OK),
    "9": StateTemplate("Committing", State.CRIT),
    "10": StateTemplate("Commit failed", State.CRIT),
    "11": StateTemplate("Standy", State.WARN),
    "12": StateTemplate("Version mismatch", State.CRIT),
    "13": StateTemplate("Name conflicted", State.CRIT),
    "14": StateTemplate("Invalid", State.CRIT),
    "15": StateTemplate("Country code mismatch", State.CRIT),
}


class RadioInfo(TypedDict):
    radio_cmk_state: State
    radio_readable_state: str
    ch_usage: float
    users_online: int


ApInfo = TypedDict(
    "ApInfo",
    {
        "cmk_status": State,
        "state_readable": str,
        "mem_used_percent": float,
        "cpu_percent": float,
        "temp": float | str,
        "con_users": str,
        "24ghz": RadioInfo,
        "5ghz": RadioInfo,
    },
)

Section = Mapping[str, ApInfo]


class HuaweiWlcApsLevelsParams(TypedDict):
    levels: tuple[float, float]


def parse_huawei_wlc_aps(string_table: Sequence[StringTable]) -> Section:
    parsed: dict[str, ApInfo] = {}

    aps_info1, aps_info2 = string_table

    for idx, ap_info1 in enumerate(aps_info1):
        if 2 * idx + 1 >= len(aps_info2):
            break

        status, mem, cpu, temp, con_users = ap_info1
        ap_id, radio_state_2GHz, ch_usage_2GHz, users_online_2GHz = aps_info2[2 * idx]
        _ap_id, radio_state_5GHz, ch_usage_5GHz, users_online_5GHz = aps_info2[2 * idx + 1]

        temp_value: float | str = "invalid" if temp == "255" else float(temp)

        parsed[ap_id] = {
            "cmk_status": _AP_STATE_MAP.get(status, _AP_UNKNOWN).value,
            "state_readable": _AP_STATE_MAP.get(status, _AP_UNKNOWN).label,
            "mem_used_percent": float(mem),
            "cpu_percent": float(cpu),
            "temp": temp_value,
            "con_users": con_users,
            "24ghz": {
                "radio_cmk_state": _RADIO_STATE_MAP.get(radio_state_2GHz, _RADIO_UNKNOWN).value,
                "radio_readable_state": _RADIO_STATE_MAP.get(
                    radio_state_2GHz, _RADIO_UNKNOWN
                ).label,
                "ch_usage": float(ch_usage_2GHz),
                "users_online": int(users_online_2GHz),
            },
            "5ghz": {
                "radio_cmk_state": _RADIO_STATE_MAP.get(radio_state_5GHz, _RADIO_UNKNOWN).value,
                "radio_readable_state": _RADIO_STATE_MAP.get(
                    radio_state_5GHz, _RADIO_UNKNOWN
                ).label,
                "ch_usage": float(ch_usage_5GHz),
                "users_online": int(users_online_5GHz),
            },
        }

    return parsed


snmp_section_huawei_wlc_aps = SNMPSection(
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


def discovery_huawei_wlc_aps_status(section: Section) -> DiscoveryResult:
    for name in section:
        yield Service(item=name)


def check_huawei_wlc_aps_status(
    item: str, params: HuaweiWlcApsLevelsParams, section: Section
) -> CheckResult:
    if not (data := section.get(item)):
        return

    yield Result(state=data["cmk_status"], summary=data["state_readable"])
    yield Result(state=State.OK, summary=f"Connected users: {data['con_users']}")

    for radio, metric, band in (
        (data["24ghz"], "24ghz", "2,4GHz"),
        (data["5ghz"], "5ghz", "5GHz"),
    ):
        yield from check_levels(
            radio["users_online"],
            metric_name=f"{metric}_clients",
            render_func=lambda x: "%d" % x,
            label=f"Users online [{band}]",
        )

        yield Result(
            state=radio["radio_cmk_state"],
            summary=f"Radio state [{band}]: {radio['radio_readable_state']}",
        )

        yield from check_levels(
            radio["ch_usage"],
            levels_upper=params["levels"],
            metric_name=f"channel_utilization_{metric}",
            render_func=render.percent,
            label=f"Channel usage [{band}]",
        )


check_plugin_huawei_wlc_aps_status = CheckPlugin(
    name="huawei_wlc_aps_status",
    service_name="AP %s Status",
    sections=["huawei_wlc_aps"],
    discovery_function=discovery_huawei_wlc_aps_status,
    check_function=check_huawei_wlc_aps_status,
    check_default_parameters={"levels": (80.0, 90.0)},
)


def discovery_huawei_wlc_aps_cpu(section: Section) -> DiscoveryResult:
    for name in section:
        yield Service(item=name)


def check_huawei_wlc_aps_cpu(
    item: str, params: HuaweiWlcApsLevelsParams, section: Section
) -> CheckResult:
    if not (data := section.get(item)):
        return

    yield from check_levels(
        data["cpu_percent"],
        levels_upper=params["levels"],
        metric_name="cpu_percent",
        render_func=render.percent,
        label="Usage",
    )


check_plugin_huawei_wlc_aps_cpu = CheckPlugin(
    name="huawei_wlc_aps_cpu",
    service_name="AP %s CPU",
    sections=["huawei_wlc_aps"],
    discovery_function=discovery_huawei_wlc_aps_cpu,
    check_function=check_huawei_wlc_aps_cpu,
    check_default_parameters={"levels": (80.0, 90.0)},
)


def discovery_huawei_wlc_aps_mem(section: Section) -> DiscoveryResult:
    for name in section:
        yield Service(item=name)


def check_huawei_wlc_aps_mem(
    item: str, params: HuaweiWlcApsLevelsParams, section: Section
) -> CheckResult:
    if not (data := section.get(item)):
        return

    yield from check_levels(
        data["mem_used_percent"],
        levels_upper=params["levels"],
        metric_name="mem_used_percent",
        render_func=render.percent,
        label="Used",
    )


check_plugin_huawei_wlc_aps_mem = CheckPlugin(
    name="huawei_wlc_aps_mem",
    service_name="AP %s Memory",
    sections=["huawei_wlc_aps"],
    discovery_function=discovery_huawei_wlc_aps_mem,
    check_function=check_huawei_wlc_aps_mem,
    check_default_parameters={"levels": (80.0, 90.0)},
)


def discovery_huawei_wlc_aps_temp(section: Section) -> DiscoveryResult:
    yield from (Service(item=name) for name in section)


def check_huawei_wlc_aps_temp(item: str, params: TempParamType, section: Section) -> CheckResult:
    if not (data := section.get(item)):
        return

    temp = data["temp"]
    # "invalid" corresponds to 255 and should *not be* alarmed as per customer's requirements
    # See SUP-1020 for details
    if isinstance(temp, float):
        yield from check_temperature(
            reading=temp,
            params=params,
            unique_name=f"AP {item} Temperature",
            value_store=get_value_store(),
        )
    else:
        yield Result(state=State.OK, summary=str(temp))


check_plugin_huawei_wlc_aps_temp = CheckPlugin(
    name="huawei_wlc_aps_temp",
    service_name="AP %s Temperature",
    sections=["huawei_wlc_aps"],
    discovery_function=discovery_huawei_wlc_aps_temp,
    check_function=check_huawei_wlc_aps_temp,
    check_default_parameters={"levels": (70.0, 75.0)},
)
