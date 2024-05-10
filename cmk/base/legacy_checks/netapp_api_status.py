#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<netapp_api_status:sep(9)>>>
# status ok


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info

from cmk.agent_based.v2 import StringTable


def inventory_netapp_api_status(info):
    return [(None, None)]


def check_netapp_api_status(item, _no_params, info):
    data = {line[0]: line[1] for line in info if len(line) == 2}

    if data.get("status"):
        state = (
            0 if data["status"].lower() in ["ok", "ok-with-suppressed", "ok_with_suppressed"] else 2
        )
        yield state, "Status: %s" % data["status"]
        del data["status"]

    for key, value in data.items():
        yield 0, f"{key.title()}: {value}"


def parse_netapp_api_status(string_table: StringTable) -> StringTable:
    return string_table


check_info["netapp_api_status"] = LegacyCheckDefinition(
    parse_function=parse_netapp_api_status,
    service_name="Diagnosis Status",
    discovery_function=inventory_netapp_api_status,
    check_function=check_netapp_api_status,
)
