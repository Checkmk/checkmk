#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.lib.bvip import DETECT_BVIP

Section = Mapping[str, str]


def parse_bvip_video_alerts(string_table: StringTable) -> Section:
    return {raw_item.replace("\x00", ""): alerts for raw_item, alerts in string_table}


snmp_section_bvip_video_alerts = SimpleSNMPSection(
    name="bvip_video_alerts",
    detect=DETECT_BVIP,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3967.1",
        oids=["1.1.3.1", "3.1.1"],
    ),
    parse_function=parse_bvip_video_alerts,
)


def inventory_bvip_video_alerts(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_bvip_video_alerts(item: str, section: Section) -> CheckResult:
    if (alerts := section.get(item)) is None:
        return

    if alerts != "0":
        yield Result(state=State.CRIT, summary="Device on Alarm State")
    else:
        yield Result(state=State.OK, summary="No alarms")


check_plugin_bvip_video_alerts = CheckPlugin(
    name="bvip_video_alerts",
    service_name="Video Alerts %s",
    discovery_function=inventory_bvip_video_alerts,
    check_function=check_bvip_video_alerts,
)
