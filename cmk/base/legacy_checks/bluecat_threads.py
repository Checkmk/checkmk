#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, startswith, StringTable

check_info = {}

threads_default_levels = {"levels": ("levels", (2000, 4000))}


def discover_bluecat_threads(info):
    if info:
        return [(None, threads_default_levels)]
    return []


def check_bluecat_threads(item, params, info):
    nthreads = int(info[0][0])
    warn, crit = None, None
    if "levels" in params and params["levels"] != "no_levels":
        warn, crit = params["levels"][1]
    perfdata = [("threads", nthreads, warn, crit, 0)]

    if crit is not None and nthreads >= crit:
        return 2, "%d threads (critical at %d)" % (nthreads, crit), perfdata
    if warn is not None and nthreads >= warn:
        return 1, "%d threads (warning at %d)" % (nthreads, warn), perfdata
    return 0, "%d threads" % (nthreads,), perfdata


def parse_bluecat_threads(string_table: StringTable) -> StringTable:
    return string_table


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
