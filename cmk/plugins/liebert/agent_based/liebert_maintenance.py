#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="arg-type"

import time
from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v1 import (
    check_levels as check_levels_v1,  # we can only use v2 after migrating the ruleset!
)
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
from cmk.plugins.liebert.agent_based.lib import (
    DETECT_LIEBERT,
    parse_liebert_without_unit,
    SectionWithoutUnit,
)

# example output
# .1.3.6.1.4.1.476.1.42.3.9.20.1.10.1.2.1.4868 Calculated Next Maintenance Month
# .1.3.6.1.4.1.476.1.42.3.9.20.1.20.1.2.1.4868 5
# .1.3.6.1.4.1.476.1.42.3.9.20.1.10.1.2.1.4869 Calculated Next Maintenance Year
# .1.3.6.1.4.1.476.1.42.3.9.20.1.20.1.2.1.4869 2017

Section = SectionWithoutUnit[int]


def parse_liebert_maintenence(string_table: StringTable) -> Section | None:
    return parse_liebert_without_unit([string_table], int) or None


def inventory_liebert_maintenance(section: Section) -> DiscoveryResult:
    yield Service()


def check_liebert_maintenance(params: Mapping[str, Any], section: Section) -> CheckResult:
    month, year = None, None
    for key, value in section.items():
        if "month" in key.lower():
            month = value
        elif "year" in key.lower():
            year = value

    if None in (month, year):
        return

    yield Result(state=State.OK, summary=f"Next maintenance: {month}/{year}")

    time_left_seconds = time.mktime((year, month, 0, 0, 0, 0, 0, 0, 0)) - time.time()

    warn_days, crit_days = params["levels"]
    yield from check_levels_v1(
        time_left_seconds,
        levels_lower=(warn_days * 86400, crit_days * 86400),
        render_func=lambda s: (
            f"{int(s // 86400)} days" if s > 0 else f"{int(-s // 86400)} days overdue"
        ),
    )


snmp_section_liebert_maintenance = SimpleSNMPSection(
    name="liebert_maintenance",
    detect=DETECT_LIEBERT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.476.1.42.3.9.20.1",
        oids=[
            "10.1.2.1.4868",
            "20.1.2.1.4868",
            "10.1.2.1.4869",
            "20.1.2.1.4869",
        ],
    ),
    parse_function=parse_liebert_maintenence,
)
check_plugin_liebert_maintenance = CheckPlugin(
    name="liebert_maintenance",
    service_name="Maintenance",
    discovery_function=inventory_liebert_maintenance,
    check_function=check_liebert_maintenance,
    check_default_parameters={"levels": (10, 5)},
)
