#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from typing import NamedTuple

from cmk.agent_based.v1 import check_levels as check_levels_v1
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
from cmk.plugins.lib.primekey import DETECT_PRIMEKEY


class _Section(NamedTuple):
    db_usage: float


def parse(string_table: StringTable) -> _Section | None:
    return _Section(float(string_table[0][0])) if string_table else None


snmp_section_primekey_db_usage = SimpleSNMPSection(
    name="primekey_db_usage",
    parse_function=parse,
    detect=DETECT_PRIMEKEY,
    fetch=SNMPTree(
        ".1.3.6.1.4.1.22408.1.1.2.1.4.118.100.98.49",
        [
            "1",  # dbUsage
        ],
    ),
)


def discover(section: _Section) -> DiscoveryResult:
    yield Service()


def check(
    params: Mapping[str, tuple[float, float]],
    section: _Section,
) -> CheckResult:
    yield from check_levels_v1(
        levels_upper=params.get("levels"),
        value=section.db_usage,
        metric_name="disk_utilization",
        label="Disk Utilization",
        render_func=render.percent,
    )


check_plugin_primekey_db_usage = CheckPlugin(
    name="primekey_db_usage",
    service_name="PrimeKey DB Usage",
    discovery_function=discover,
    check_function=check,
    check_default_parameters={"levels": (80.0, 90.0)},
    check_ruleset_name="db_usage",
)
