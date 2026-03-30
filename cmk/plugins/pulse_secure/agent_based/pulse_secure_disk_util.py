#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import TypedDict

from cmk.agent_based.v1 import check_levels
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.pulse_secure import lib as pulse_secure

Section = Mapping[str, int]

METRIC_PULSE_SECURE_DISK = "disk_utilization"


class PulseSecureDiskUtilParams(TypedDict, total=False):
    upper_levels: tuple[float, float]


def parse_pulse_secure_disk_util(string_table: StringTable) -> Section | None:
    return pulse_secure.parse_pulse_secure(string_table, METRIC_PULSE_SECURE_DISK)


def discover_pulse_secure_disk_util(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


def check_pulse_secure_disk_util(
    params: PulseSecureDiskUtilParams, section: Section
) -> CheckResult:
    if not section:
        return

    yield from check_levels(
        section[METRIC_PULSE_SECURE_DISK],
        levels_upper=params.get("upper_levels"),
        metric_name=METRIC_PULSE_SECURE_DISK,
        render_func=render.percent,
        label="Percentage of disk space used",
    )


snmp_section_pulse_secure_disk_util = SimpleSNMPSection(
    name="pulse_secure_disk_util",
    detect=pulse_secure.DETECT_PULSE_SECURE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12532",
        oids=["25"],
    ),
    parse_function=parse_pulse_secure_disk_util,
)


check_plugin_pulse_secure_disk_util = CheckPlugin(
    name="pulse_secure_disk_util",
    service_name="Pulse Secure disk utilization",
    discovery_function=discover_pulse_secure_disk_util,
    check_function=check_pulse_secure_disk_util,
    check_ruleset_name="pulse_secure_disk_util",
    check_default_parameters={"upper_levels": (80.0, 90.0)},
)
