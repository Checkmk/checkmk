#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Mapping

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.lib.cpu_util import check_cpu_util
from cmk.plugins.pulse_secure import lib as pulse_secure

Section = Mapping[str, int]

KEY_PULSE_SECURE_CPU = "cpu_util"


def parse_pulse_secure_cpu_util(string_table: StringTable) -> Section | None:
    return pulse_secure.parse_pulse_secure(string_table, KEY_PULSE_SECURE_CPU)


def discover_pulse_secure_cpu_util(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


def check_pulse_secure_cpu(params: Mapping[str, object], section: Section) -> CheckResult:
    if not section:
        return

    yield from check_cpu_util(
        util=float(section[KEY_PULSE_SECURE_CPU]),
        params=params,
        value_store=get_value_store(),
        this_time=time.time(),
    )


snmp_section_pulse_secure_cpu_util = SimpleSNMPSection(
    name="pulse_secure_cpu_util",
    detect=pulse_secure.DETECT_PULSE_SECURE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12532",
        oids=["10"],
    ),
    parse_function=parse_pulse_secure_cpu_util,
)


check_plugin_pulse_secure_cpu_util = CheckPlugin(
    name="pulse_secure_cpu_util",
    service_name="Pulse Secure IVE CPU utilization",
    discovery_function=discover_pulse_secure_cpu_util,
    check_function=check_pulse_secure_cpu,
    check_ruleset_name="cpu_utilization",
    check_default_parameters={"util": (80.0, 90.0)},
)
