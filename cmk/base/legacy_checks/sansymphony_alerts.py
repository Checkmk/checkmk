#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import StringTable

check_info = {}


def discover_sansymphony_alerts(info):
    yield None, {}


def check_sansymphony_alerts(_no_item, params, info):
    nr_of_alerts = int(info[0][0])
    yield check_levels(
        nr_of_alerts,
        "alerts",
        params["levels"],
        human_readable_func=str,
        infoname="Unacknowlegded alerts",
    )


def parse_sansymphony_alerts(string_table: StringTable) -> StringTable:
    return string_table


check_info["sansymphony_alerts"] = LegacyCheckDefinition(
    name="sansymphony_alerts",
    parse_function=parse_sansymphony_alerts,
    service_name="sansymphony Alerts",
    discovery_function=discover_sansymphony_alerts,
    check_function=check_sansymphony_alerts,
    check_ruleset_name="sansymphony_alerts",
    check_default_parameters={
        "levels": (1, 2),
    },
)
