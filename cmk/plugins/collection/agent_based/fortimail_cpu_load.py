#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

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
from cmk.plugins.lib.fortinet import DETECT_FORTIMAIL

Section = Mapping[str, float]


def parse_fortimail_cpu_load(string_table: StringTable) -> Section | None:
    """
    >>> parse_fortimail_cpu_load([["5"]])
    {'cpu_load': 5.0}
    """
    return {"cpu_load": float(string_table[0][0])} if string_table else None


def discovery_fortimail_cpu_load(section: Section) -> DiscoveryResult:
    yield Service()


def check_fortimail_cpu_load(
    params: Mapping[str, tuple[float, float] | None],
    section: Section,
) -> CheckResult:
    yield from check_levels_v1(
        section["cpu_load"],
        levels_upper=params["cpu_load"],
        metric_name="load_instant",
        label="CPU load",
    )


snmp_section_fortimail_cpu_load = SimpleSNMPSection(
    name="fortimail_cpu_load",
    parse_function=parse_fortimail_cpu_load,
    detect=DETECT_FORTIMAIL,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12356.105.1",
        oids=[
            "30",  # fmlSysLoad
        ],
    ),
)

check_plugin_fortimail_cpu_load = CheckPlugin(
    name="fortimail_cpu_load",
    service_name="CPU load",
    discovery_function=discovery_fortimail_cpu_load,
    check_function=check_fortimail_cpu_load,
    check_default_parameters={"cpu_load": None},
    check_ruleset_name="fortimail_cpu_load",
)
