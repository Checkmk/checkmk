#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.hitachi_hnas.lib import DETECT

_FITTED_STATUS_MAP = (
    ("ok", State.OK),  # 1
    ("okIdWrong", State.WARN),  # 2
    ("notFitted", State.CRIT),  # 3
    ("unknown", State.WARN),  # 4
)

_SPEED_STATUS_MAP = (
    ("ok", State.OK),  # 1
    ("warning", State.WARN),  # 2
    ("severe", State.CRIT),  # 3
    ("unknown", State.WARN),  # 4
)


def parse_hitachi_hnas_fan(string_table: StringTable) -> StringTable:
    return string_table


def discover_hitachi_hnas_fan(section: StringTable) -> DiscoveryResult:
    for clusternode, fan_id, _fitted_status, _speed_status, _speed in section:
        yield Service(item=f"{clusternode}.{fan_id}")


def check_hitachi_hnas_fan(item: str, section: StringTable) -> CheckResult:
    for clusternode, fan_id, fitted_status, speed_status, speed in section:
        if f"{clusternode}.{fan_id}" != item:
            continue

        yield Result(state=State.OK, summary=f"PNode {clusternode} fan {fan_id}")

        name, state = _FITTED_STATUS_MAP[int(fitted_status) - 1]
        yield Result(state=state, summary=f"Fitted status is {name}")

        name, state = _SPEED_STATUS_MAP[int(speed_status) - 1]
        yield Result(state=state, summary=f"Speed status is {name}")

        yield Result(state=State.OK, summary=f"Speed is {speed} rpm")
        yield Metric("fanspeed", int(speed), boundaries=(0, None))
        return

    yield Result(state=State.UNKNOWN, summary=f"No fan {item} found")


snmp_section_hitachi_hnas_fan = SimpleSNMPSection(
    name="hitachi_hnas_fan",
    parse_function=parse_hitachi_hnas_fan,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.11096.6.1.1.1.2.1.11.1",
        oids=["1", "2", "3", "4", "5"],
    ),
)


check_plugin_hitachi_hnas_fan = CheckPlugin(
    name="hitachi_hnas_fan",
    service_name="Fan %s",
    discovery_function=discover_hitachi_hnas_fan,
    check_function=check_hitachi_hnas_fan,
)
