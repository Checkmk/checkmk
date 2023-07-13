#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="list-item"

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.cpu_util import check_cpu_util
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import any_of, equals, SNMPTree, startswith


def parse_brocade_sys(info):
    try:
        return {
            "cpu_util": int(info[0][0]),
            "mem_used_percent": int(info[0][1]),
        }
    except (IndexError, ValueError):
        return {}


#   .--Memory--------------------------------------------------------------.
#   |               __  __                                                 |
#   |              |  \/  | ___ _ __ ___   ___  _ __ _   _                 |
#   |              | |\/| |/ _ \ '_ ` _ \ / _ \| '__| | | |                |
#   |              | |  | |  __/ | | | | | (_) | |  | |_| |                |
#   |              |_|  |_|\___|_| |_| |_|\___/|_|   \__, |                |
#   |                                                |___/                 |
#   '----------------------------------------------------------------------'


def inventory_brocade_sys_mem(parsed):
    yield None, {}


def check_brocade_sys_mem(item, params, parsed):
    mem_used_percent = parsed["mem_used_percent"]
    infotext = "%s%%" % mem_used_percent
    if not params:
        perfdata = [("mem_used_percent", mem_used_percent)]
        return 0, infotext, perfdata

    warn, crit = params
    perfdata = [("mem_used_percent", mem_used_percent, warn, crit)]
    levelstext = " (warn/crit at %d/%d%%)" % (warn, crit)
    if mem_used_percent >= crit:
        status = 2
    elif mem_used_percent >= warn:
        status = 1
    else:
        status = 0
    if status:
        infotext += levelstext
    return status, infotext, perfdata


check_info["brocade_sys.mem"] = LegacyCheckDefinition(
    service_name="Memory",
    discovery_function=inventory_brocade_sys_mem,
    check_function=check_brocade_sys_mem,
    check_ruleset_name="memory_relative",
)

# .
#   .--CPU-----------------------------------------------------------------.
#   |                           ____ ____  _   _                           |
#   |                          / ___|  _ \| | | |                          |
#   |                         | |   | |_) | | | |                          |
#   |                         | |___|  __/| |_| |                          |
#   |                          \____|_|    \___/                           |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def inventory_brocade_sys(parsed):
    return [(None, {})]


def check_brocade_sys(item, params, parsed):
    return check_cpu_util(parsed["cpu_util"], params)


check_info["brocade_sys"] = LegacyCheckDefinition(
    detect=any_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.1588.2.1.1"),
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.1916.2.306"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.1588.2.1.1.1.26",
        oids=["1", "6"],
    ),
    parse_function=parse_brocade_sys,
    service_name="CPU utilization",
    discovery_function=inventory_brocade_sys,
    check_function=check_brocade_sys,
    check_ruleset_name="cpu_utilization",
)
