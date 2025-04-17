#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
from collections.abc import Generator, Mapping
from datetime import datetime, UTC
from enum import Enum
from typing import Any, Final, Literal, NamedTuple

from cmk.agent_based.v2 import (
    AgentSection,
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Result,
    Service,
    State,
    StringTable,
)

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
    location: str | None
    group_name: str
    mobility_group_name: str | None
    alarm_status: AlarmStatus
    access_points_count: int
    client_count: int
    reachability_status: bool
    last_backup: datetime | None


def get_controllers(controller_data: dict[str, Any]) -> Generator[dict[str, Any], None, None]:
    for entity in controller_data["queryResponse"]["entity"]:
        dto_type = entity["@dtoType"]
        yield entity[dto_type]


def get_last_backup(last_backup: str | None) -> datetime | None:
    if not last_backup:
        return None

    return datetime.strptime(last_backup, "%Y-%m-%dT%H:%M:%S.%f%z")


def parse_cisco_prime_wlan_controller(string_table: StringTable) -> dict[str, WlanController]:
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


agent_section_cisco_prime_wlan_controller = AgentSection(
    name="cisco_prime_wlan_controller",
    parse_function=parse_cisco_prime_wlan_controller,
)


def discovery_wlan_controller(section: dict[str, WlanController]) -> DiscoveryResult:
    for item in section:
        yield Service(item=item)


def check_wlan_controller_metadata(item: str, section: dict[str, WlanController]) -> CheckResult:
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


check_plugin_cisco_prime_wlan_controller_metadata = CheckPlugin(
    name="cisco_prime_wlan_controller_metadata",
    sections=["cisco_prime_wlan_controller"],
    service_name="Cisco Prime WLAN Controller %s",
    discovery_function=discovery_wlan_controller,
    check_function=check_wlan_controller_metadata,
)


def check_wlan_controller_alarm_status(
    item: str, section: dict[str, WlanController]
) -> CheckResult:
    data = section.get(item)
    if not data:
        return

    state = ALARM_STATE_MAPPING[data.alarm_status]
    yield Result(state=state, summary=data.alarm_status.name)


check_plugin_cisco_prime_wlan_controller_alarm_status = CheckPlugin(
    name="cisco_prime_wlan_controller_alarm_status",
    sections=["cisco_prime_wlan_controller"],
    service_name="Cisco Prime WLAN Controller %s Alarm Status",
    discovery_function=discovery_wlan_controller,
    check_function=check_wlan_controller_alarm_status,
)


def check_wlan_controller_access_points(
    item: str,
    params: Mapping[
        str,
        tuple[Literal["no_levels"], None]
        | tuple[Literal["fixed"], tuple[int, int] | tuple[float, float]]
        | tuple[Literal["predictive"], tuple[str, float | None, tuple[float, float] | None]],
    ],
    section: dict[str, WlanController],
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


check_plugin_cisco_prime_wlan_controller_access_points = CheckPlugin(
    name="cisco_prime_wlan_controller_access_points",
    sections=["cisco_prime_wlan_controller"],
    service_name="Cisco Prime WLAN Controller %s Access Points",
    discovery_function=discovery_wlan_controller,
    check_function=check_wlan_controller_access_points,
    check_ruleset_name="cisco_prime_wlan_controller_access_points",
    check_default_parameters={},
)


def check_wlan_controller_clients(
    item: str,
    params: Mapping[
        str,
        tuple[Literal["no_levels"], None]
        | tuple[Literal["fixed"], tuple[int, int] | tuple[float, float]]
        | tuple[Literal["predictive"], tuple[str, float | None, tuple[float, float] | None]],
    ],
    section: dict[str, WlanController],
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


check_plugin_cisco_prime_wlan_controller_clients = CheckPlugin(
    name="cisco_prime_wlan_controller_clients",
    sections=["cisco_prime_wlan_controller"],
    service_name="Cisco Prime WLAN Controller %s Clients",
    discovery_function=discovery_wlan_controller,
    check_function=check_wlan_controller_clients,
    check_ruleset_name="cisco_prime_wlan_controller_clients",
    check_default_parameters={},
)


def check_wlan_controller_reachability(
    item: str, section: dict[str, WlanController]
) -> CheckResult:
    data = section.get(item)
    if not data:
        return

    if data.reachability_status:
        yield Result(state=State.OK, summary="REACHABLE")
        return

    yield Result(state=State.CRIT, summary="UNREACHABLE")


check_plugin_cisco_prime_wlan_controller_reachability = CheckPlugin(
    name="cisco_prime_wlan_controller_reachability",
    sections=["cisco_prime_wlan_controller"],
    service_name="Cisco Prime WLAN Controller %s Reachability",
    discovery_function=discovery_wlan_controller,
    check_function=check_wlan_controller_reachability,
)


def check_wlan_controller_last_backup(
    item: str,
    params: Mapping[
        str,
        tuple[Literal["no_levels"], None]
        | tuple[Literal["fixed"], tuple[int, int] | tuple[float, float]]
        | tuple[Literal["predictive"], tuple[str, float | None, tuple[float, float] | None]],
    ],
    section: dict[str, WlanController],
) -> CheckResult:
    data = section.get(item)
    if not data:
        return

    if not data.last_backup:
        yield Result(state=State.WARN, summary="No backup")
        return

    yield from check_levels(
        (datetime.now(UTC) - data.last_backup).total_seconds(),
        levels_upper=params["last_backup"],
        metric_name="backup_age",
        render_func=render.timespan,
    )


check_plugin_cisco_prime_wlan_controller_last_backup = CheckPlugin(
    name="cisco_prime_wlan_controller_last_backup",
    sections=["cisco_prime_wlan_controller"],
    service_name="Cisco Prime WLAN Controller %s Last Backup",
    discovery_function=discovery_wlan_controller,
    check_function=check_wlan_controller_last_backup,
    check_ruleset_name="cisco_prime_wlan_controller_last_backup",
    check_default_parameters={
        "last_backup": (7.0 * DAY_IN_SECONDS, 30.0 * DAY_IN_SECONDS),
    },
)
