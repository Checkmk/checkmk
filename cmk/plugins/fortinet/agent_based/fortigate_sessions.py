#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v1 import check_levels as check_levels_v1
from cmk.agent_based.v2 import (
    all_of,
    CheckPlugin,
    CheckResult,
    contains,
    DiscoveryResult,
    exists,
    not_exists,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)

Section = int


def parse_fortigate_sessions(string_table: StringTable) -> Section | None:
    try:
        return int(string_table[0][0])
    except IndexError, ValueError:
        return None


def discover_fortigate_sessions(section: Section) -> DiscoveryResult:
    yield Service()


def check_fortigate_sessions(params: Mapping[str, Any], section: Section) -> CheckResult:
    yield from check_levels_v1(
        section,
        metric_name="session",
        levels_upper=params["levels"],
        render_func=str,
        label="Sessions",
    )


snmp_section_fortigate_sessions = SimpleSNMPSection(
    name="fortigate_sessions",
    detect=all_of(
        contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.12356.101.1"),
        exists(".1.3.6.1.4.1.12356.1.10.0"),
        not_exists(".1.3.6.1.4.1.12356.101.4.1.8.0"),
    ),
    # uses mib FORTINET-MIB-280,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12356.1",
        oids=["10"],
    ),
    parse_function=parse_fortigate_sessions,
)


check_plugin_fortigate_sessions = CheckPlugin(
    name="fortigate_sessions",
    service_name="Sessions",
    discovery_function=discover_fortigate_sessions,
    check_function=check_fortigate_sessions,
    check_ruleset_name="fortigate_sessions",
    check_default_parameters={"levels": (100000, 150000)},
)
