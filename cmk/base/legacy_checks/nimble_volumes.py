#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, startswith, StringTable
from cmk.base.check_legacy_includes.df import df_check_filesystem_list, FILESYSTEM_DEFAULT_PARAMS

check_info = {}

# example output


def discover_nimble_volumes(info):
    for line in info:
        if line[4] == "1":
            yield (line[1], {})


def check_nimble_volumes(item, params, info):
    for line in info:
        if line[1] == item:
            if line[4] == "0":
                yield 3, "Volume is offline!"
                continue
            total = int(line[2])
            free = total - int(line[3])
            yield df_check_filesystem_list(item, params, [(item, total, free, 0)])


def parse_nimble_volumes(string_table: StringTable) -> StringTable:
    return string_table


check_info["nimble_volumes"] = LegacyCheckDefinition(
    name="nimble_volumes",
    parse_function=parse_nimble_volumes,
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.37447.3.1"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.37447.1.2.1",
        oids=["2", "3", "4", "6", "10"],
    ),
    service_name="Volume %s",
    discovery_function=discover_nimble_volumes,
    check_function=check_nimble_volumes,
    check_ruleset_name="filesystem",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)
