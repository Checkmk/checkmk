#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="possibly-undefined"

# mypy: disable-error-code="arg-type"
# mypy: disable-error-code="no-untyped-def"

# <<<appdynamics_memory:sep(124)>>>
# Hans|Non-Heap|Max Available (MB):304|Current Usage (MB):78|Used %:25|Committed (MB):267
# Hans|Heap|Max Available (MB):455|Current Usage (MB):66|Used %:14|Committed (MB):252

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import render, StringTable

check_info = {}


def discover_appdynamics_memory(info):
    for line in info:
        yield " ".join(line[0:2]), {}


def check_appdynamics_memory(item, params, info):
    for line in info:
        if item == " ".join(line[0:2]):
            mb = 1024 * 1024.0

            if item.endswith("Non-Heap"):
                mem_type = "nonheap"
            elif item.endswith("Heap"):
                mem_type = "heap"
            else:
                mem_type = ""  # Should not happen...

            values = {}
            for metric in line[2:]:
                name, value = metric.split(":")
                values[name] = int(value)

            used = values.get("Current Usage (MB)", 0) * mb
            committed = values.get("Committed (MB)", 0) * mb

            try:
                max_available = values["Max Available (MB)"] * mb
            except KeyError:
                max_available = -1  # Java 8 has no maximum for Non-Heap

            if max_available > 0:
                used_percent = 100.0 * used / max_available

                warn, crit = params.get(mem_type, (None, None))
            else:
                warn, crit = (None, None)

            if isinstance(crit, float):
                crit_label = "%.2f%%" % crit
                crit = int((max_available / 100.0) * crit)
            elif isinstance(crit, int):
                crit_label = "%d MB free" % (crit)
                crit = max_available - (crit * mb)
            else:
                crit_label = ""

            if isinstance(warn, float):
                warn_label = "%.2f%%" % warn
                warn = int((max_available / 100.0) * warn)
            elif isinstance(warn, int):
                warn_label = "%d MB free" % (warn)
                warn = max_available - (warn * mb)
            else:
                warn_label = ""

            state = 0
            if crit and used >= crit:
                state = 2
            elif warn and used >= warn:
                state = 1

            levels_label = ""
            if state > 0:
                levels_label = f" (levels at {warn_label}/{crit_label})"

            if max_available > 0:
                yield (
                    state,
                    f"Used: {render.bytes(used)} of {render.bytes(max_available)} ({used_percent:.2f}%){levels_label}",
                    [("mem_%s" % mem_type, used, warn, crit, 0, max_available)],
                )
                yield (
                    0,
                    "Committed: %s" % render.bytes(committed),
                    [("mem_%s_committed" % mem_type, committed, None, None, 0, max_available)],
                )
            else:
                yield state, "Used: %s" % render.bytes(used), [("mem_%s" % mem_type, used)]
                yield (
                    0,
                    "Committed: %s" % render.bytes(committed),
                    [("mem_%s_committed" % mem_type, committed)],
                )


def parse_appdynamics_memory(string_table: StringTable) -> StringTable:
    return string_table


check_info["appdynamics_memory"] = LegacyCheckDefinition(
    name="appdynamics_memory",
    parse_function=parse_appdynamics_memory,
    service_name="AppDynamics Memory %s",
    discovery_function=discover_appdynamics_memory,
    check_function=check_appdynamics_memory,
    check_ruleset_name="jvm_memory",
)
