#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import check_levels, LegacyCheckDefinition, saveint
from cmk.base.config import check_info

from cmk.agent_based.v2 import all_of, exists, SNMPTree, startswith, StringTable


def inventory_enterasys_lsnat(info):
    return [(None, {})]


def check_enterasys_lsnat(_no_item, params, info):
    if not info:
        return

    lsnat_bindings = saveint(info[0][0])

    yield check_levels(
        lsnat_bindings,
        "current_bindings",
        params.get("current_bindings"),
        infoname="Current bindings",
        human_readable_func=str,
    )


def parse_enterasys_lsnat(string_table: StringTable) -> StringTable | None:
    return string_table or None


check_info["enterasys_lsnat"] = LegacyCheckDefinition(
    parse_function=parse_enterasys_lsnat,
    detect=all_of(
        startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.5624.2.1"),
        exists(".1.3.6.1.4.1.5624.1.2.74.1.1.5.0"),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.5624.1.2.74.1.1.5",
        oids=["0"],
    ),
    service_name="LSNAT Bindings",
    discovery_function=inventory_enterasys_lsnat,
    check_function=check_enterasys_lsnat,
    check_ruleset_name="lsnat",
    check_default_parameters={
        "current_bindings": None,
    },
)
