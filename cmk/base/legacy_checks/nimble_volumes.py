#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="assignment"

from cmk.base.check_api import startswith
from cmk.base.check_legacy_includes.df import df_check_filesystem_list, FILESYSTEM_DEFAULT_PARAMS
from cmk.base.config import check_info, factory_settings
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree

# example output

factory_settings["filesystem_default_levels"] = FILESYSTEM_DEFAULT_PARAMS


def inventory_nimble_volumes(info):
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


check_info["nimble_volumes"] = {
    "detect": startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.37447.3.1"),
    "discovery_function": inventory_nimble_volumes,
    "check_function": check_nimble_volumes,
    "service_name": "Volume %s",
    "fetch": SNMPTree(
        base=".1.3.6.1.4.1.37447.1.2.1",
        oids=["2", "3", "4", "6", "10"],
    ),
    "check_ruleset_name": "filesystem",
    "default_levels_variable": "filesystem_default_levels",
}
