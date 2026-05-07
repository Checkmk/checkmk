#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    startswith,
    State,
    StringTable,
)


def parse_bluecat_threads(string_table: StringTable) -> StringTable | None:
    return string_table or None


def discover_bluecat_threads(section: StringTable) -> DiscoveryResult:
    yield Service()


def check_bluecat_threads(
    params: Mapping[str, Any],
    section: StringTable,
) -> CheckResult:
    nthreads = int(section[0][0])
    warn, crit = None, None
    if "levels" in params and params["levels"] != "no_levels":
        warn, crit = params["levels"][1]

    if crit is not None and nthreads >= crit:
        yield Result(state=State.CRIT, summary=f"{nthreads} threads (critical at {crit})")
    elif warn is not None and nthreads >= warn:
        yield Result(state=State.WARN, summary=f"{nthreads} threads (warning at {warn})")
    else:
        yield Result(state=State.OK, summary=f"{nthreads} threads")
    yield Metric("threads", nthreads, levels=(warn, crit) if warn is not None else None)


snmp_section_bluecat_threads = SimpleSNMPSection(
    name="bluecat_threads",
    parse_function=parse_bluecat_threads,
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.13315.100.200"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.13315.100.200.1.1.2",
        oids=["1"],
    ),
)

check_plugin_bluecat_threads = CheckPlugin(
    name="bluecat_threads",
    service_name="Number of threads",
    discovery_function=discover_bluecat_threads,
    check_function=check_bluecat_threads,
    check_ruleset_name="threads",
    check_default_parameters={"levels": ("levels", (2000, 4000))},
)
