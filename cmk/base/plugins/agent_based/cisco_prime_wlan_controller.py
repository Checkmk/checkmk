#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Final, Generator, Mapping, NamedTuple, Optional, Tuple

from .agent_based_api.v1 import check_levels, register, render, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable

DAY_IN_SECONDS = 24 * 60 * 60


class AlarmStatus(Enum):
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    WARNING = "warning"
    CLEARED = "cleared"
    INFORMATION = "information"


ALARM_STATE_MAPPING: Final = {
    AlarmStatus.CRITICAL: State.CRIT,
    AlarmStatus.MAJOR: State.CRIT,
    AlarmStatus.MINOR: State.WARN,
    AlarmStatus.WARNING: State.WARN,
    AlarmStatus.CLEARED: State.OK,
    AlarmStatus.INFORMATION: State.OK,
}


class WlanController(NamedTuple):
    name: str
    type: str
    software_version: str
    ip_address: str
    location: Optional[str]
    group_name: str
    mobility_group_name: Optional[str]
    alarm_status: AlarmStatus
    access_points_count: int
    client_count: int
    reachability_status: bool
    last_backup: Optional[datetime]


def get_controllers(controller_data: Dict[str, Any]) -> Generator[Dict[str, Any], None, None]:
    for entity in controller_data["queryResponse"]["entity"]:
        dto_type = entity["@dtoType"]
        yield entity[dto_type]


def get_last_backup(last_backup: Optional[str]) -> Optional[datetime]:
    if not last_backup:
        return None

    return datetime.strptime(last_backup, "%Y-%m-%dT%H:%M:%S.%f%z")


def parse_cisco_prime_wlan_controller(string_table: StringTable) -> Dict[str, WlanController]:
    controller_data = json.loads(string_table[0][0])

    return {
        c["name"]: WlanController(
            name=c["name"],
            type=c["type"],
            software_version=c["softwareVersion"],
            ip_address=c["ipAddress"],
            location=c.get("location"),
            group_name=c["rfGroupName"],
            mobility_group_name=c.get("mobilityGroupName"),
            alarm_status=AlarmStatus(c["alarmStatus"].lower()),
            access_points_count=c["apCount"],
            client_count=c["clientCount"],
            reachability_status=c["reachabilityStatus"],
            last_backup=get_last_backup(c.get("lastBackup")),
        )
        for c in get_controllers(controller_data)
    }


register.agent_section(
    name="cisco_prime_wlan_controller",
    parse_function=parse_cisco_prime_wlan_controller,
)


def discovery_wlan_controller(section: Dict[str, WlanController]) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


def check_wlan_controller_metadata(item: str, section: Dict[str, WlanController]) -> CheckResult:
    data = section.get(item)
    if not data:
        return

    yield Result(state=State.OK, notice=f"Name: {data.name}")
    yield Result(state=State.OK, summary=f"Type: {data.type}")
    yield Result(state=State.OK, summary=f"Software version: {data.software_version}")
    yield Result(state=State.OK, notice=f"IP address: {data.ip_address}")

    if data.location:
        yield Result(state=State.OK, summary=f"Location: {data.location}")

    yield Result(state=State.OK, summary=f"Group name: {data.group_name}")

    if data.mobility_group_name:
        yield Result(state=State.OK, summary=f"Mobility group name: {data.mobility_group_name}")


register.check_plugin(
    name="cisco_prime_wlan_controller_metadata",
    sections=["cisco_prime_wlan_controller"],
    service_name="Cisco Prime WLAN Controller %s",
    discovery_function=discovery_wlan_controller,
    check_function=check_wlan_controller_metadata,
)


def check_wlan_controller_alarm_status(
    item: str, section: Dict[str, WlanController]
) -> CheckResult:
    data = section.get(item)
    if not data:
        return

    state = ALARM_STATE_MAPPING[data.alarm_status]
    yield Result(state=state, summary=data.alarm_status.name)


register.check_plugin(
    name="cisco_prime_wlan_controller_alarm_status",
    sections=["cisco_prime_wlan_controller"],
    service_name="Cisco Prime WLAN Controller %s Alarm Status",
    discovery_function=discovery_wlan_controller,
    check_function=check_wlan_controller_alarm_status,
)


def check_wlan_controller_access_points(
    item: str, params: Mapping[str, Tuple[float, float]], section: Dict[str, WlanController]
) -> CheckResult:
    data = section.get(item)
    if not data:
        return

    yield from check_levels(
        data.access_points_count,
        levels_upper=params.get("access_points"),
        label="Count",
        metric_name="ap_count",
        render_func=lambda x: str(int(x)),
    )


register.check_plugin(
    name="cisco_prime_wlan_controller_access_points",
    sections=["cisco_prime_wlan_controller"],
    service_name="Cisco Prime WLAN Controller %s Access Points",
    discovery_function=discovery_wlan_controller,
    check_function=check_wlan_controller_access_points,
    check_ruleset_name="cisco_prime_wlan_controller_access_points",
    check_default_parameters={},
)


def check_wlan_controller_clients(
    item: str, params: Mapping[str, Tuple[float, float]], section: Dict[str, WlanController]
) -> CheckResult:
    data = section.get(item)
    if not data:
        return

    yield from check_levels(
        data.client_count,
        levels_upper=params.get("clients"),
        label="Count",
        metric_name="clients_count",
        render_func=lambda x: str(int(x)),
    )


register.check_plugin(
    name="cisco_prime_wlan_controller_clients",
    sections=["cisco_prime_wlan_controller"],
    service_name="Cisco Prime WLAN Controller %s Clients",
    discovery_function=discovery_wlan_controller,
    check_function=check_wlan_controller_clients,
    check_ruleset_name="cisco_prime_wlan_controller_clients",
    check_default_parameters={},
)


def check_wlan_controller_reachability(
    item: str, section: Dict[str, WlanController]
) -> CheckResult:
    data = section.get(item)
    if not data:
        return

    if data.reachability_status:
        yield Result(state=State.OK, summary="REACHABLE")
        return

    yield Result(state=State.CRIT, summary="UNREACHABLE")


register.check_plugin(
    name="cisco_prime_wlan_controller_reachability",
    sections=["cisco_prime_wlan_controller"],
    service_name="Cisco Prime WLAN Controller %s Reachability",
    discovery_function=discovery_wlan_controller,
    check_function=check_wlan_controller_reachability,
)


def check_wlan_controller_last_backup(
    item: str, params: Mapping[str, Tuple[float, float]], section: Dict[str, WlanController]
) -> CheckResult:
    data = section.get(item)
    if not data:
        return

    if not data.last_backup:
        yield Result(state=State.WARN, summary="No backup")
        return

    yield from check_levels(
        (datetime.now(timezone.utc) - data.last_backup).total_seconds(),
        levels_upper=params["last_backup"],
        metric_name="backup_age",
        render_func=render.timespan,
    )


register.check_plugin(
    name="cisco_prime_wlan_controller_last_backup",
    sections=["cisco_prime_wlan_controller"],
    service_name="Cisco Prime WLAN Controller %s Last Backup",
    discovery_function=discovery_wlan_controller,
    check_function=check_wlan_controller_last_backup,
    check_ruleset_name="cisco_prime_wlan_controller_last_backup",
    check_default_parameters={"last_backup": (7 * DAY_IN_SECONDS, 30 * DAY_IN_SECONDS)},
)
