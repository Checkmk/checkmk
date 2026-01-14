#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import any_of, equals, render, SNMPTree, startswith
from cmk.base.check_legacy_includes.cpu_util import check_cpu_util

check_info = {}


def parse_brocade_sys(string_table):
    try:
        return {
            "cpu_util": int(string_table[0][0]),
            "mem_used_percent": int(string_table[0][1]),
        }
    except (IndexError, ValueError):
        return None


#   .--Memory--------------------------------------------------------------.
#   |               __  __                                                 |
#   |              |  \/  | ___ _ __ ___   ___  _ __ _   _                 |
#   |              | |\/| |/ _ \ '_ ` _ \ / _ \| '__| | | |                |
#   |              | |  | |  __/ | | | | | (_) | |  | |_| |                |
#   |              |_|  |_|\___|_| |_| |_|\___/|_|   \__, |                |
#   |                                                |___/                 |
#   '----------------------------------------------------------------------'


def discover_brocade_sys_mem(parsed):
    yield None, {}


def check_brocade_sys_mem(item, params, parsed):
    yield check_levels(
        parsed["mem_used_percent"],
        "mem_used_percent",
        params["levels"],
        human_readable_func=render.percent,
    )


check_info["brocade_sys.mem"] = LegacyCheckDefinition(
    name="brocade_sys_mem",
    service_name="Memory",
    sections=["brocade_sys"],
    discovery_function=discover_brocade_sys_mem,
    check_function=check_brocade_sys_mem,
    check_ruleset_name="memory_relative",
    check_default_parameters={"levels": None},
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


def discover_brocade_sys(parsed):
    return [(None, {})]


def check_brocade_sys(item, params, parsed):
    return check_cpu_util(parsed["cpu_util"], params)


check_info["brocade_sys"] = LegacyCheckDefinition(
    name="brocade_sys",
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
    discovery_function=discover_brocade_sys,
    check_function=check_brocade_sys,
    check_ruleset_name="cpu_utilization",
)
