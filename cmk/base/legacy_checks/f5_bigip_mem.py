#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.mem import check_memory_element
from cmk.base.config import check_info

from cmk.agent_based.v2 import contains, SNMPTree

# FIXME
# The WATO group 'memory_simple' needs an item and the service_description should
# have a '%s'.  At the moment the current item 'total'/'TMM' and 'Memory' without '%s'
# works but is not consistent.  This will be fixed in the future.
# If we change this we loose history and parameter sets have to be adapted.

# Example output:
# Overall memory
# .1.3.6.1.4.1.3375.2.1.7.1.1.0 8396496896 sysHostMemoryTotal
# .1.3.6.1.4.1.3375.2.1.7.1.2.0 1331092416 sysHostMemoryUsed
#
# TMM (Traffic Management Module) memory
# .1.3.6.1.4.1.3375.2.1.1.2.1.143 0 sysStatMemoryTotalKb
# .1.3.6.1.4.1.3375.2.1.1.2.1.144 0 sysStatMemoryUsedKb


def parse_f5_bigip_mem(string_table):
    parsed = {}
    try:
        parsed["total"] = (float(string_table[0][0]), float(string_table[0][1]))
    except ValueError:
        pass

    try:
        parsed["TMM"] = (float(string_table[0][2]) * 1024, float(string_table[0][3]) * 1024)
    except ValueError:
        pass

    return parsed


def discover_f5_bigip_mem(parsed):
    if "total" in parsed:
        yield "total", {}


def check_f5_bigip_mem(_item, params, parsed):
    if "total" not in parsed:
        return None

    mem_total, mem_used = parsed["total"]
    return check_memory_element(
        "Usage",
        mem_used,
        mem_total,
        params.get("levels"),
        metric_name="mem_used",
    )


check_info["f5_bigip_mem"] = LegacyCheckDefinition(
    detect=contains(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.3375"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3375.2.1",
        oids=["7.1.1", "7.1.2", "1.2.1.143", "1.2.1.144"],
    ),
    parse_function=parse_f5_bigip_mem,
    service_name="Memory",
    discovery_function=discover_f5_bigip_mem,
    check_function=check_f5_bigip_mem,
    check_ruleset_name="memory_simple",
    check_default_parameters={"levels": ("perc_used", (80.0, 90.0))},
)


def discover_f5_bigip_mem_tmm(parsed):
    if parsed.get("TMM", (0, 0))[0] > 0:
        yield "TMM", {}


def check_f5_bigip_mem_tmm(_item, params, parsed):
    if "TMM" not in parsed:
        return None

    mem_total, mem_used = parsed["TMM"]
    return check_memory_element(
        "Usage",
        mem_used,
        mem_total,
        params.get("levels"),
        metric_name="mem_used",
    )


check_info["f5_bigip_mem.tmm"] = LegacyCheckDefinition(
    service_name="Memory",
    sections=["f5_bigip_mem"],
    discovery_function=discover_f5_bigip_mem_tmm,
    check_function=check_f5_bigip_mem_tmm,
    check_ruleset_name="memory_simple",
    check_default_parameters={"levels": ("perc_used", (80.0, 90.0))},
)
