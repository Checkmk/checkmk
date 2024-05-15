#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import StringTable


def inventory_netapp_api_connection(info):
    yield None, {}


def check_netapp_api_connection(_no_item, params, info):
    state = 0
    infos = []
    suppressed_warnings = 0
    warning_overrides = params["warning_overrides"]

    for line in info:
        line = " ".join(line)
        line_state = 1

        for entry in warning_overrides:
            if line.startswith(entry.get("name")):
                line_state = entry.get("state")

        if line_state == 0:
            suppressed_warnings += 1
        else:
            infos.append(line)

        state = max(state, line_state)

    if suppressed_warnings:
        infos.append(
            "%d suppressed warning%s by WATO rule"
            % (suppressed_warnings, suppressed_warnings > 1 and "s" or "")
        )

    if infos:
        return state, ", ".join(infos)
    return 0, "The agent was able to retrieve all data from the filer"


def parse_netapp_api_connection(string_table: StringTable) -> StringTable:
    return string_table


check_info["netapp_api_connection"] = LegacyCheckDefinition(
    parse_function=parse_netapp_api_connection,
    service_name="NetApp filer connection",
    discovery_function=inventory_netapp_api_connection,
    check_function=check_netapp_api_connection,
    check_ruleset_name="netapp_instance",
    check_default_parameters={"warning_overrides": []},
)
