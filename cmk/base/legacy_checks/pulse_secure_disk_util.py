#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Mapping

from cmk.base.check_api import check_levels, LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import render, SNMPTree

import cmk.plugins.lib.pulse_secure as pulse_secure
from cmk.agent_based.v2.type_defs import StringTable

Section = Mapping[str, int]

METRIC_PULSE_SECURE_DISK = "disk_utilization"


def parse_pulse_secure_disk_util(string_table: StringTable) -> Section:
    return pulse_secure.parse_pulse_secure(string_table, METRIC_PULSE_SECURE_DISK)


def discover_pulse_secure_disk_util(section: Section) -> Iterable[tuple[None, dict]]:
    if section:
        yield None, {}


def check_pulse_secure_disk_util(item, params, parsed):
    if not parsed:
        return None

    yield check_levels(
        parsed[METRIC_PULSE_SECURE_DISK],
        METRIC_PULSE_SECURE_DISK,
        params.get("upper_levels"),
        infoname="Percentage of disk space used",
        human_readable_func=render.percent,
    )
    return None


check_info["pulse_secure_disk_util"] = LegacyCheckDefinition(
    detect=pulse_secure.DETECT_PULSE_SECURE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12532",
        oids=["25"],
    ),
    parse_function=parse_pulse_secure_disk_util,
    service_name="Pulse Secure disk utilization",
    discovery_function=discover_pulse_secure_disk_util,
    check_function=check_pulse_secure_disk_util,
    check_ruleset_name="pulse_secure_disk_util",
    check_default_parameters={"upper_levels": (80.0, 90.0)},
)
