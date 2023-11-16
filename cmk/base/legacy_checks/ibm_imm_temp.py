#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree

from cmk.plugins.lib.ibm import DETECT_IBM_IMM


def inventory_ibm_imm_temp(info):
    for line in info:
        if line[1] != "0":
            yield line[0], {}


def check_ibm_imm_temp(item, params, info):
    for line in info:
        if line[0] == item:
            try:
                temp = float(line[1])
            except ValueError:
                return None

            try:
                dev_levels = float(line[3]), float(line[2])
            except ValueError:
                dev_levels = None

            try:
                dev_levels_lower = float(line[5]), float(line[4])
            except ValueError:
                dev_levels_lower = None

            return check_temperature(
                temp,
                params,
                "ibm_imm_temp_%s" % item,
                dev_levels=dev_levels,
                dev_levels_lower=dev_levels_lower,
            )
    return None


check_info["ibm_imm_temp"] = LegacyCheckDefinition(
    detect=DETECT_IBM_IMM,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.2.3.51.3.1.1.2.1",
        oids=["2", "3", "6", "7", "9", "10"],
    ),
    service_name="Temperature %s",
    discovery_function=inventory_ibm_imm_temp,
    check_function=check_ibm_imm_temp,
    check_ruleset_name="temperature",
)
