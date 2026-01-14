#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.base.check_legacy_includes.cisco_ucs import DETECT

check_info = {}

# comNET GmbH, Fabian Binder - 2018-05-30

# .1.3.6.1.4.1.9.9.719.1.9.35.1.9   cucsComputeRackUnitAvailableMemory


def discover_cisco_ucs_mem_total(info):
    return [(None, None)]


def check_cisco_ucs_mem_total(_no_item, _no_params, info):
    total_memory = info[0][0]
    return 0, "Total Memory: %s MB" % total_memory


def parse_cisco_ucs_mem_total(string_table: StringTable) -> StringTable | None:
    return string_table or None


check_info["cisco_ucs_mem_total"] = LegacyCheckDefinition(
    name="cisco_ucs_mem_total",
    parse_function=parse_cisco_ucs_mem_total,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9.9.719.1.9.35.1",
        oids=["9"],
    ),
    service_name="Memory total",
    discovery_function=discover_cisco_ucs_mem_total,
    check_function=check_cisco_ucs_mem_total,
)
