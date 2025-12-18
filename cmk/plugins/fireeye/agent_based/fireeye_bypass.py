#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.fireeye.lib import DETECT

# .1.3.6.1.4.1.25597.13.1.41.0 0
# .1.3.6.1.4.1.25597.13.1.42.0 0
# .1.3.6.1.4.1.25597.13.1.43.0 0


def discover_bypass(section: StringTable) -> DiscoveryResult:
    if section:
        value = int(section[0][0])
        yield Service(parameters={"value": value})


def check_fireeye_bypass(params: Mapping[str, Any], section: StringTable) -> CheckResult:
    expected_value = params.get("value", 0)
    current_value = int(section[0][0])
    yield Result(state=State.OK, summary=f"Bypass E-Mail count: {current_value}")
    if current_value != expected_value:
        yield Result(state=State.CRIT, summary=f" (was {expected_value} before)")


def parse_fireeye_bypass(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_fireeye_bypass = SimpleSNMPSection(
    name="fireeye_bypass",
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.25597.13.1",
        oids=["41"],
    ),
    parse_function=parse_fireeye_bypass,
)


check_plugin_fireeye_bypass = CheckPlugin(
    name="fireeye_bypass",
    service_name="Bypass Mail Rate",
    discovery_function=discover_bypass,
    check_function=check_fireeye_bypass,
    check_default_parameters={"value": 0},
)
