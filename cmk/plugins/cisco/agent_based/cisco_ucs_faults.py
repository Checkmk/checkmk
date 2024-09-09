#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    State,
)
from cmk.plugins.collection.agent_based.cisco_ucs_fault_section import Section
from cmk.plugins.lib.cisco_ucs import check_cisco_fault


def discover_cisco_ucs_faults(section: Section) -> DiscoveryResult:
    yield Service()


def check_cisco_ucs_faults(section: Section) -> CheckResult:
    if not section:
        yield Result(state=State.OK, summary="No faults")
        return

    for fault in section.values():
        yield from check_cisco_fault(fault)


check_plugin_cisco_ucs_faults = CheckPlugin(
    name="cisco_ucs_faults",
    sections=["cisco_ucs_fault"],
    service_name="Cisco UCS Faults",
    discovery_function=discover_cisco_ucs_faults,
    check_function=check_cisco_ucs_faults,
)
