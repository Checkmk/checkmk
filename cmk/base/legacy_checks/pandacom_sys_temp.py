#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.check_legacy_includes.temperature import check_temperature

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, StringTable
from cmk.plugins.lib.pandacom import DETECT_PANDACOM

check_info = {}


def parse_pandacom_sys_temp(string_table: StringTable) -> StringTable | None:
    return string_table or None


def inventory_pandacom_sys_temp(info):
    return [("System", {})]


def check_pandacom_sys_temp(item, params, info):
    return check_temperature(int(info[0][0]), params, "pandacom_sys_%s" % item)


check_info["pandacom_sys_temp"] = LegacyCheckDefinition(
    name="pandacom_sys_temp",
    parse_function=parse_pandacom_sys_temp,
    detect=DETECT_PANDACOM,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3652.3.1.1",
        oids=["6"],
    ),
    service_name="Temperature %s",
    discovery_function=inventory_pandacom_sys_temp,
    check_function=check_pandacom_sys_temp,
    check_ruleset_name="temperature",
    check_default_parameters={"levels": (35.0, 40.0)},
)
