#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    OIDEnd,
    Result,
    Service,
    SNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.stulz.lib import DETECT_STULZ


def parse_stulz_pump(string_table: Sequence[StringTable]) -> Sequence[StringTable]:
    return string_table


def discover_stulz_pump(section: Sequence[StringTable]) -> DiscoveryResult:
    for pump_id, _pump_status in section[0]:
        yield Service(item=pump_id.replace(".1", ""))


def check_stulz_pump(item: str, section: Sequence[StringTable]) -> CheckResult:
    for index, (pump_id, pump_status) in enumerate(section[0]):
        pump_id = pump_id.replace(".1", "")
        if pump_id == item:
            pump_rpm = section[1][index][0]
            if pump_status == "1":
                yield Result(state=State.OK, summary=f"Pump is running at {pump_rpm}%")
            elif pump_status == "0":
                yield Result(state=State.CRIT, summary="Pump is not running")
            else:
                yield Result(
                    state=State.UNKNOWN,
                    summary=f"Pump reports unidentified status {pump_status}",
                )
            yield Metric("rpm", float(pump_rpm), boundaries=(0.0, 100.0))
            return


snmp_section_stulz_pump = SNMPSection(
    name="stulz_pump",
    detect=DETECT_STULZ,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.4.1.29462.10.2.1.1.2.1.4.1.1.5802",
            oids=[OIDEnd(), "2"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.29462.10.2.1.1.2.1.4.1.1.5821",
            oids=["2"],
        ),
    ],
    parse_function=parse_stulz_pump,
)

check_plugin_stulz_pump = CheckPlugin(
    name="stulz_pump",
    service_name="Pump %s",
    discovery_function=discover_stulz_pump,
    check_function=check_stulz_pump,
)
