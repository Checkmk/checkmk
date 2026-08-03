#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
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
from cmk.plugins.ibm_imm.lib import DETECT_IBM_IMM


def discover_ibm_imm_fan(section: StringTable) -> DiscoveryResult:
    for descr, speed_text in section:
        if speed_text.lower() != "offline":
            yield Service(item=descr)


def check_ibm_imm_fan(item: str, params: Mapping[str, Any], section: StringTable) -> CheckResult:
    for descr, speed_text in section:
        if descr == item:
            if speed_text.lower() in ["offline", "unavailable"]:
                yield Result(state=State.CRIT, summary=f"is {speed_text.lower()}")
                return

            # speed_text can be "34 %", or "34%", or "34 % of maximum"
            # or simply a text without quotes..
            rpm_perc = int(speed_text.strip().replace('["%]', " ").replace("%", " ").split(" ")[0])

            yield from check_levels_v1(
                value=rpm_perc,
                levels_upper=params["levels"],
                levels_lower=params["levels_lower"],
                label="% of max RPM",
                render_func=lambda v: f"{v:.0f}%",
            )


def parse_ibm_imm_fan(string_table: StringTable) -> StringTable:
    return string_table


snmp_section_ibm_imm_fan = SimpleSNMPSection(
    name="ibm_imm_fan",
    detect=DETECT_IBM_IMM,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2.3.51.3.1.3.2.1",
        oids=["2", "3"],
    ),
    parse_function=parse_ibm_imm_fan,
)


check_plugin_ibm_imm_fan = CheckPlugin(
    name="ibm_imm_fan",
    service_name="Fan %s",
    discovery_function=discover_ibm_imm_fan,
    check_function=check_ibm_imm_fan,
    check_ruleset_name="hw_fans_perc",
    check_default_parameters={
        "levels_lower": (28.0, 25.0),  # Just a guess. Please give feedback.
    },
)
