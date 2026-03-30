#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

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

METRIC_PULSE_SECURE_LOG = "log_file_utilization"


def parse_pulse_secure_log_utils(string_table: StringTable) -> Section | None:
    return pulse_secure.parse_pulse_secure(string_table, METRIC_PULSE_SECURE_LOG)


def discover_pulse_secure_log_util(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


def check_pulse_secure_log_util(section: Section) -> CheckResult:
    if not section:
        return

    yield from check_levels(
        section[METRIC_PULSE_SECURE_LOG],
        metric_name=METRIC_PULSE_SECURE_LOG,
        render_func=render.percent,
        label="Percentage of log file used",
    )


snmp_section_pulse_secure_log_util = SimpleSNMPSection(
    name="pulse_secure_log_util",
    detect=pulse_secure.DETECT_PULSE_SECURE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12532",
        oids=["1"],
    ),
    parse_function=parse_pulse_secure_log_utils,
)


check_plugin_pulse_secure_log_util = CheckPlugin(
    name="pulse_secure_log_util",
    service_name="Pulse Secure log file utilization",
    discovery_function=discover_pulse_secure_log_util,
    check_function=check_pulse_secure_log_util,
)
