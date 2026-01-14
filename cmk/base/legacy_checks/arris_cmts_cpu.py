#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import equals, OIDEnd, SNMPTree, StringTable

check_info = {}


def discover_arris_cmts_cpu(info):
    for oid_id, cpu_id, _cpu_idle_util in info:
        # Sadly the cpu_id seams empty. Referring to
        # the MIB, its slot id
        # Fallback to the oid end
        yield cpu_id or str(int(oid_id) - 1), {}


def check_arris_cmts_cpu(item, params, info):
    for oid_id, cpu_id, cpu_idle_util in info:
        # see inventory function
        if cpu_id:
            citem = cpu_id
        else:
            citem = str(int(oid_id) - 1)

        if citem == item:
            # We get the IDLE percentage, but need the usage
            cpu_util = 100 - int(cpu_idle_util)
            warn, crit = params["levels"]

            infotext = "Current utilization is: %d %% " % cpu_util
            levels = f" (warn/crit at {warn:.1f}/{crit:.1f} %)"
            perfdata = [("util", cpu_util, warn, crit)]
            if cpu_util >= crit:
                yield 2, infotext + levels, perfdata
            elif cpu_util >= warn:
                yield 1, infotext + levels, perfdata
            else:
                yield 0, infotext, perfdata
            return


def parse_arris_cmts_cpu(string_table: StringTable) -> StringTable:
    return string_table


check_info["arris_cmts_cpu"] = LegacyCheckDefinition(
    name="arris_cmts_cpu",
    parse_function=parse_arris_cmts_cpu,
    detect=equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.4998.2.1"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.4998.1.1.5.3.1.1.1",
        oids=[OIDEnd(), "1", "8"],
    ),
    service_name="CPU utilization Module %s",
    discovery_function=discover_arris_cmts_cpu,
    check_function=check_arris_cmts_cpu,
    check_ruleset_name="cpu_utilization_multiitem",
    check_default_parameters={"levels": (90.0, 95.0)},
)
