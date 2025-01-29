#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from contextlib import suppress

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.emc import DETECT_ISILON

Section = Mapping[str, int]


def parse_emc_isilon_iops(string_table: StringTable) -> Section:
    parsed = {}
    for name, iops_str in string_table:
        with suppress(ValueError):
            parsed[name] = int(iops_str)
    return parsed


snmp_section_emc_isilon_iops = SimpleSNMPSection(
    name="emc_isilon_iops",
    detect=DETECT_ISILON,
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
    yield from check_levels_v1(
        iops,
        metric_name="iops",
        label="Disk operations",
        render_func=lambda d: "%d/s" % d,
    )


check_plugin_emc_isilon_iops = CheckPlugin(
    name="emc_isilon_iops",
    service_name="Disk %s IO",
    discovery_function=discover_emc_isilon_iops,
    check_function=check_emc_isilon_iops,
)
