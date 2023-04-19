#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from datetime import datetime

from .agent_based_api.v1 import register, Result, Service, State
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.cisco_meraki import check_last_reported_ts, load_json, MerakiAPIData


@dataclass(frozen=True)
class DeviceStatus:
    status: str
    last_reported: datetime | None

    @classmethod
    def parse(cls, row: MerakiAPIData) -> "DeviceStatus":
        return cls(
            status=str(row["status"]),
            last_reported=cls._parse_last_reported(str(row["lastReportedAt"])),
        )

    @staticmethod
    def _parse_last_reported(raw_last_reported: str) -> datetime | None:
        try:
            return datetime.strptime(raw_last_reported, "%Y-%m-%dT%H:%M:%S.%fZ")
        except ValueError:
            return None


def parse_device_status(string_table: StringTable) -> DeviceStatus | None:
    return DeviceStatus.parse(loaded_json[0]) if (loaded_json := load_json(string_table)) else None


register.agent_section(
    name="cisco_meraki_org_device",
    parse_function=parse_device_status,
)


def discover_device_status(section: DeviceStatus | None) -> DiscoveryResult:
    if section and section.status != "offline":
        yield Service()


_STATUS_MAP = {
    "online": State.OK,
    "alerting": State.CRIT,
    "offline": State.WARN,
    "dormant": State.WARN,  # TODO not sure
}


def check_device_status(section: DeviceStatus | None) -> CheckResult:
    if not section:
        return

    yield Result(
        state=_STATUS_MAP.get(section.status, State.UNKNOWN),
        summary=f"Status: {section.status}",
    )

    if section.last_reported is not None:
        yield from check_last_reported_ts(section.last_reported.timestamp())


register.check_plugin(
    name="cisco_meraki_org_device_status",
    sections=["cisco_meraki_org_device"],
    service_name="Cisco Meraki Device Status",
    discovery_function=discover_device_status,
    check_function=check_device_status,
)
