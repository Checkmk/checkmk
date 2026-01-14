#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree
from cmk.base.check_legacy_includes.mem import check_memory_element
from cmk.plugins.fortinet.lib import DETECT_FORTIGATE
from cmk.plugins.lib.memory import get_levels_mode_from_value, LevelsMode

check_info = {}


def parse_fortigate_memory_base(string_table):
    try:
        total = int(string_table[0][1]) * 1024  # value from device is in kb, we need bytes
        used = float(string_table[0][0]) / 100.0 * total
    except (IndexError, ValueError):
        return ()
    return used, total


def discover_fortigate_memory_base(parsed):
    if parsed:
        yield None, {}


def check_fortigate_memory_base(_item, params, parsed):
    if isinstance(params, tuple):
        levels: tuple[LevelsMode, tuple[float, float]] = ("perc_used", params)
    else:
        warn, crit = params["levels"]
        mode = get_levels_mode_from_value(warn)
        # Rule 'memory' uses MiB for absolute values:
        scale = 1.0 if mode.startswith("perc") else 2**20
        levels = (mode, (abs(warn) * scale, abs(crit) * scale))

    if not parsed:
        return None
    used, total = parsed

    return check_memory_element("Used", used, total, levels, metric_name="mem_used")


check_info["fortigate_memory_base"] = LegacyCheckDefinition(
    name="fortigate_memory_base",
    detect=DETECT_FORTIGATE,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.12356.101.4.1",
        oids=["4", "5"],
    ),
    parse_function=parse_fortigate_memory_base,
    service_name="Memory",
    discovery_function=discover_fortigate_memory_base,
    check_function=check_fortigate_memory_base,
    check_ruleset_name="memory",
    check_default_parameters={"levels": (70.0, 80.0)},
)
