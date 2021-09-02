#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from contextlib import suppress
from typing import Mapping

from .agent_based_api.v1 import check_levels, contains, register, Service, SNMPTree
from .agent_based_api.v1.type_defs import CheckResult, DiscoveryResult, StringTable

Section = Mapping[str, int]


def parse_emc_isilon_iops(string_table: StringTable) -> Section:
    parsed = {}
    for name, iops_str in string_table:
        with suppress(ValueError):
            parsed[name] = int(iops_str)
    return parsed


register.snmp_section(
    name="emc_isilon_iops",
    detect=contains(
        ".1.3.6.1.2.1.1.1.0",
        "isilon",
    ),
    fetch=SNMPTree(
        ".1.3.6.1.4.1.12124.2.2.52.1",
        [
            "2",  # diskPerfDeviceName
            "3",  # diskPerfOpsPerSecond
        ],
    ),
    parse_function=parse_emc_isilon_iops,
)


def discover_emc_isilon_iops(section: Section) -> DiscoveryResult:
    yield from (Service(item=item) for item in section)


def check_emc_isilon_iops(
    item: str,
    section: Section,
) -> CheckResult:
    if (iops := section.get(item)) is None:
        return
    yield from check_levels(
        iops,
        metric_name="iops",
        label="Disk operations",
        render_func=lambda d: "%d/s" % d,
    )


register.check_plugin(
    name="emc_isilon_iops",
    service_name="Disk %s IO",
    discovery_function=discover_emc_isilon_iops,
    check_function=check_emc_isilon_iops,
)
