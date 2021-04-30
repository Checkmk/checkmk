#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping, Optional, Tuple

from .agent_based_api.v1 import check_levels, register, Service, SNMPTree
from .agent_based_api.v1.render import percent
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable
from .utils.fortinet import DETECT_FORTIMAIL

Section = Mapping[str, float]


def parse_fortimail_disk_usage(string_table: StringTable) -> Optional[Section]:
    """
    >>> parse_fortimail_disk_usage([["13"]])
    {'disk_usage': 13.0}
    """
    return {"disk_usage": float(string_table[0][0])} if string_table else None


def discover_fortimail_disk_usage(section: Section) -> DiscoveryResult:
    yield Service()


def check_fortimail_disk_usage(
    params: Mapping[str, Optional[Tuple[float, float]]],
    section: Section,
) -> CheckResult:
    yield from check_levels(
        section["disk_usage"],
        levels_upper=params["disk_usage"],
        metric_name="disk_utilization",
        label="Disk usage",
        render_func=percent,
    )


register.snmp_section(
    name="fortimail_disk_usage",
    parse_function=parse_fortimail_disk_usage,
    detect=DETECT_FORTIMAIL,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12356.105.1",
        oids=[
            "9",  # fmlSysMailDiskUsage
        ],
    ),
)

register.check_plugin(
    name="fortimail_disk_usage",
    service_name="Disk usage",
    discovery_function=discover_fortimail_disk_usage,
    check_function=check_fortimail_disk_usage,
    check_default_parameters={"disk_usage": (80, 90)},
    check_ruleset_name="fortimail_disk_usage",
)
