#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from time import time
from typing import Mapping, Tuple

from .agent_based_api.v1 import (
    check_levels,
    get_rate,
    get_value_store,
    OIDEnd,
    register,
    Service,
    SNMPTree,
)
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.fortinet import DETECT_FORTIGATE

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
    params: Mapping[str, Tuple[float, float]],
    section: Section,
) -> CheckResult:
    if item not in section:
        return

    data = section[item]
    value_store = get_value_store()
    now = time()
    yield from check_levels(
        get_rate(value_store, "detection_rate", now, data["detected"]),
        levels_upper=params["detections"],
        metric_name="fortigate_detection_rate",
        label="Detection rate",
        render_func=lambda v: f"{v:.2f}/s",
    )
    yield from check_levels(
        get_rate(value_store, "blocking rate", now, data["blocked"]),
        metric_name="fortigate_blocking_rate",
        label="Blocking rate",
        render_func=lambda v: f"{v:.2f}/s",
    )


register.snmp_section(
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

register.snmp_section(
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

register.check_plugin(
    name="fortigate_antivirus",
    service_name="AntiVirus %s",
    discovery_function=discover_fortigate_antivirus_ips,
    check_function=check_fortigate_antivirus_ips,
    check_ruleset_name="fortigate_antivirus",
    check_default_parameters={"detections": (100, 300)},
)

register.check_plugin(
    name="fortigate_ips",
    service_name="IPS %s",
    discovery_function=discover_fortigate_antivirus_ips,
    check_function=check_fortigate_antivirus_ips,
    check_ruleset_name="fortigate_ips",
    check_default_parameters={"detections": (100, 300)},
)
