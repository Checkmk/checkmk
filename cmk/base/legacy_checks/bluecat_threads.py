#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.agent_based.legacy.v0_unstable import (
    check_levels,
    LegacyCheckDefinition,
    LegacyCheckResult,
    LegacyDiscoveryResult,
)
from cmk.agent_based.v2 import SNMPTree, startswith, StringTable

check_info = {}

type Section = int

threads_default_levels = {"levels": ("levels", (2000, 4000))}


def discover_bluecat_threads(info: StringTable) -> LegacyDiscoveryResult:
    if info:
        return [(None, threads_default_levels)]
    return []


def check_bluecat_threads(
    _no_item: None, params: Mapping[str, Any], section: Section
) -> LegacyCheckResult:
    nthreads = section
    warn, crit = None, None
    if "levels" in params and params["levels"] != "no_levels":
        warn, crit = params["levels"][1]

    yield check_levels(
        nthreads, "threads", params=(warn, crit), human_readable_func=str, boundaries=(0.0, None)
    )


def parse_bluecat_threads(string_table: StringTable) -> Section:
    return int(string_table[0][0])


check_info["bluecat_threads"] = LegacyCheckDefinition(
    name="bluecat_threads",
    parse_function=parse_bluecat_threads,
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.13315.100.200"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.13315.100.200.1.1.2",
        oids=["1"],
    ),
    service_name="Number of threads",
    discovery_function=discover_bluecat_threads,
    check_function=check_bluecat_threads,
    check_ruleset_name="threads",
)
