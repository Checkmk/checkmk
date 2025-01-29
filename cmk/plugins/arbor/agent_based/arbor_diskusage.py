#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    render,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.df import FILESYSTEM_DEFAULT_PARAMS

from .lib import DETECT_PEAKFLOW_SP, DETECT_PEAKFLOW_TMS, DETECT_PRAVAIL


def parse_arbor_disk_usage(string_table: StringTable) -> int | None:
    return int(string_table[0][0]) if string_table else None


snmp_section_arbor_diskusage_peakflow_sp = SimpleSNMPSection(
    name="arbor_peakflow_sp_disk_usage",
    detect=DETECT_PEAKFLOW_SP,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9694.1.4.2.1",
        oids=["4.0"],
    ),
    parse_function=parse_arbor_disk_usage,
)


def discover_arbor_disk_usage(section: int) -> DiscoveryResult:
    yield Service(item="/")


def check_arbor_disk_usage(item: str, params: Mapping[str, Any], section: int) -> CheckResult:
    yield from check_levels_v1(
        section, levels_upper=params["levels"], label="Disk usage", render_func=render.percent
    )
    yield Metric("disk_utilization", float(section) / 100.0)


check_plugin_arbor_peakflow_sp_disk_usage = CheckPlugin(
    name="arbor_peakflow_sp_disk_usage",
    service_name="Disk Usage %s",
    discovery_function=discover_arbor_disk_usage,
    check_function=check_arbor_disk_usage,
    # I lack the time to fix this. The plug-in ignores most of the parameters,
    # and it applies some of them wrongly. There might be a configration that works.
    check_ruleset_name="filesystem",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)


def parse_arbor_peakflow_tms_disk_usage(string_table: StringTable) -> int | None:
    return int(string_table[0][0]) if string_table else None


snmp_section_arbor_diskusage_peakflow_tms = SimpleSNMPSection(
    name="arbor_peakflow_tms_disk_usage",
    detect=DETECT_PEAKFLOW_TMS,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9694.1.5.2",
        oids=["6.0"],
    ),
    parse_function=parse_arbor_disk_usage,
)


check_plugin_arbor_peakflow_tms_disk_usage = CheckPlugin(
    name="arbor_peakflow_tms_disk_usage",
    service_name="Disk Usage %s",
    discovery_function=discover_arbor_disk_usage,
    check_function=check_arbor_disk_usage,
    # I lack the time to fix this. The plug-in ignores most of the parameters,
    # and it applies some of them wrongly. There might be a configration that works.
    check_ruleset_name="filesystem",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)


snmp_section_arbor_diskusage_pravail = SimpleSNMPSection(
    name="arbor_pravail_disk_usage",
    detect=DETECT_PRAVAIL,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9694.1.6.2",
        oids=["6.0"],
    ),
    parse_function=parse_arbor_disk_usage,
)

check_plugin_arbor_pravail_disk_usage = CheckPlugin(
    name="arbor_pravail_disk_usage",
    service_name="Disk Usage %s",
    discovery_function=discover_arbor_disk_usage,
    check_function=check_arbor_disk_usage,
    # I lack the time to fix this. The plug-in ignores most of the parameters,
    # and it applies some of them wrongly. There might be a configration that works.
    check_ruleset_name="filesystem",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)
