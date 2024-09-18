#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from typing import Any, Literal

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)

from .lib import DETECT_PRAVAIL


def parse_arbor_drop_rate(string_table: StringTable) -> int | None:
    return int(string_table[0][0]) if string_table else None


snmp_section_arbor_pravail_drop_rate = SimpleSNMPSection(
    name="arbor_pravail_drop_rate",
    detect=DETECT_PRAVAIL,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9694.1.6.2",
        oids=["39.0"],
    ),
    parse_function=parse_arbor_drop_rate,
)


def discover_arbor_drop_rate(section: int) -> DiscoveryResult:
    yield Service(item="Overrun")


def check_arbor_drop_rate(
    item: Literal["Overrun"], params: Mapping[str, Any], section: int
) -> CheckResult:
    yield from check_levels_v1(
        section,
        metric_name="if_in_pkts",
        levels_lower=params.get("levels_lower"),
        levels_upper=params.get("levels"),
        render_func=lambda x: "%.1f pps",
    )


check_plugin_arbor_pravail_drop_rate = CheckPlugin(
    name="arbor_pravail_drop_rate",
    service_name="%s drop rate",
    discovery_function=discover_arbor_drop_rate,
    check_function=check_arbor_drop_rate,
    check_ruleset_name="generic_rate",
    check_default_parameters={},
)
