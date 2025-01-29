#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from time import time

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_rate,
    get_value_store,
    OIDEnd,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.fortinet import DETECT_FORTIGATE

Section = Mapping[str, Mapping[str, int]]


def parse_fortigate_antivirus_ips(string_table: StringTable) -> Section:
    """
    >>> parse_fortigate_antivirus_ips([["101", "2", "3"], ["102", "4", "5"]])
    {'101': {'detected': 2, 'blocked': 3}, '102': {'detected': 4, 'blocked': 5}}
    """
    return {
        sub_table[0]: {
            "detected": int(sub_table[1]),
            "blocked": int(sub_table[2]),
        }
        for sub_table in string_table
    }


def discover_fortigate_antivirus_ips(section: Section) -> DiscoveryResult:
    yield from (Service(item=key) for key in section)


def check_fortigate_antivirus_ips(
    item: str,
    params: Mapping[str, tuple[float, float]],
    section: Section,
) -> CheckResult:
    if item not in section:
        return

    data = section[item]
    value_store = get_value_store()
    now = time()
    yield from check_levels_v1(
        get_rate(value_store, "detection_rate", now, data["detected"]),
        levels_upper=params["detections"],
        metric_name="fortigate_detection_rate",
        label="Detection rate",
        render_func=lambda v: f"{v:.2f}/s",
    )
    yield from check_levels_v1(
        get_rate(value_store, "blocking rate", now, data["blocked"]),
        metric_name="fortigate_blocking_rate",
        label="Blocking rate",
        render_func=lambda v: f"{v:.2f}/s",
    )


snmp_section_fortigate_antivirus = SimpleSNMPSection(
    name="fortigate_antivirus",
    parse_function=parse_fortigate_antivirus_ips,
    detect=DETECT_FORTIGATE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12356.101.8.2.1.1",
        oids=[
            OIDEnd(),
            "1",  # fgAvVirusDetected
            "2",  # fgAvVirusBlocked
        ],
    ),
)

snmp_section_fortigate_ips = SimpleSNMPSection(
    name="fortigate_ips",
    parse_function=parse_fortigate_antivirus_ips,
    detect=DETECT_FORTIGATE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12356.101.9.2.1.1",
        oids=[
            OIDEnd(),
            "1",  # fgIpsIntrusionsDetected
            "2",  # fgIpsIntrusionsBlocked
        ],
    ),
)

check_plugin_fortigate_antivirus = CheckPlugin(
    name="fortigate_antivirus",
    service_name="AntiVirus %s",
    discovery_function=discover_fortigate_antivirus_ips,
    check_function=check_fortigate_antivirus_ips,
    check_ruleset_name="fortigate_antivirus",
    check_default_parameters={"detections": (100.0, 300.0)},
)

check_plugin_fortigate_ips = CheckPlugin(
    name="fortigate_ips",
    service_name="IPS %s",
    discovery_function=discover_fortigate_antivirus_ips,
    check_function=check_fortigate_antivirus_ips,
    check_ruleset_name="fortigate_ips",
    check_default_parameters={"detections": (100.0, 300.0)},
)
