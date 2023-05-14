#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition, startswith
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree

threads_default_levels = {"levels": ("levels", (2000, 4000))}


def inventory_bluecat_threads(info):
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


check_info["bluecat_threads"] = LegacyCheckDefinition(
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.13315.100.200"),
    check_function=check_bluecat_threads,
    discovery_function=inventory_bluecat_threads,
    service_name="Number of threads",
    check_ruleset_name="threads",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.13315.100.200.1.1.2",
        oids=["1"],
    ),
)
