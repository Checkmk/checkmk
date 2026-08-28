#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

import time
from collections.abc import Mapping
from typing import Any

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
from cmk.plugins.fortinet.lib import DETECT_FORTISANDBOX
from cmk.plugins.lib.cpu_util import check_cpu_util

# Nikolas Hagemann, comNET GmbH - nikolas.hagemann@comnetgmbh.com

# Example output:
# .1.3.6.1.4.1.12356.118.3.1.3.0 10

Section = int


def parse_fortisandbox_cpu_util(string_table: StringTable) -> Section | None:
    try:
        return int(string_table[0][0])
    except IndexError, ValueError:
        return None


def discover_fortisandbox_cpu_util(section: Section) -> DiscoveryResult:
    yield Service()


def check_fortisandbox_cpu_util(params: Mapping[str, Any], section: Section) -> CheckResult:
    yield from check_cpu_util(
        util=section,
        params=params,
        value_store=get_value_store(),
        this_time=time.time(),
    )


snmp_section_fortisandbox_cpu_util = SimpleSNMPSection(
    name="fortisandbox_cpu_util",
    detect=DETECT_FORTISANDBOX,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12356.118.3.1",
        oids=["3"],
    ),
    parse_function=parse_fortisandbox_cpu_util,
)


check_plugin_fortisandbox_cpu_util = CheckPlugin(
    name="fortisandbox_cpu_util",
    service_name="CPU utilization",
    discovery_function=discover_fortisandbox_cpu_util,
    check_function=check_fortisandbox_cpu_util,
    check_ruleset_name="cpu_utilization",
    check_default_parameters={},
)
