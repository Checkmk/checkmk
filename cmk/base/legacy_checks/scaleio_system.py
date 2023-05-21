#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.df import df_check_filesystem_list, FILESYSTEM_DEFAULT_PARAMS
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import StringTable
from cmk.base.plugins.agent_based.utils.scaleio import parse_scaleio, ScaleioSection

# <<<scaleio_system:sep(9)>>>
# SYSTEM 5914d6b47d479d5a:
#        ID                                                 5914d6b47d479d5a
#        NAME                                               N/A
#        CAPACITY_ALERT_HIGH_THRESHOLD                      80%
#        CAPACITY_ALERT_CRITICAL_THRESHOLD                  90%
#        MAX_CAPACITY_IN_KB                                 65.5 TB (67059 GB)
#        UNUSED_CAPACITY_IN_KB                              17.2 TB (17635 GB)
#


def parse_scaleio_system(string_table: StringTable) -> ScaleioSection:
    return parse_scaleio(string_table, "SYSTEM")


def inventory_scaleio_system(parsed):
    for entry in parsed:
        yield entry, {}


def check_scaleio_system(item, params, parsed):
    if not (data := parsed.get(item)):
        return

    if "levels" not in params:
        params["levels"] = (
            float(data["CAPACITY_ALERT_HIGH_THRESHOLD"][0].strip("%")),
            float(data["CAPACITY_ALERT_CRITICAL_THRESHOLD"][0].strip("%")),
        )
    total = int(data["MAX_CAPACITY_IN_KB"][2].strip("(")) * 1024
    free = int(data["UNUSED_CAPACITY_IN_KB"][2].strip("(")) * 1024

    yield df_check_filesystem_list(item, params, [(item, total, free, 0)])


check_info["scaleio_system"] = LegacyCheckDefinition(
    parse_function=parse_scaleio_system,
    discovery_function=inventory_scaleio_system,
    check_function=check_scaleio_system,
    service_name="ScaleIO System %s",
    check_ruleset_name="filesystem",
    check_default_parameters=FILESYSTEM_DEFAULT_PARAMS,
)
