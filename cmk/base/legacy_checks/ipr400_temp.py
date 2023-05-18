#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition, startswith
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree


def inventory_ipr400_temp(info):
    if len(info) > 0:
        yield "Ambient", None


def check_ipr400_temp(item, params, info):
    return check_temperature(int(info[0][0]), params, "ipr400_temp_%s" % item)


check_info["ipr400_temp"] = LegacyCheckDefinition(
    detect=startswith(".1.3.6.1.2.1.1.1.0", "ipr voip device ipr400"),
    check_function=check_ipr400_temp,
    discovery_function=inventory_ipr400_temp,
    service_name="Temperature %s ",
    check_ruleset_name="temperature",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.27053.1.4.5",
        oids=["9"],
    ),
    check_default_parameters={
        "levels": (30.0, 40.0),  # reported temperature seems to be near room temperature usually
    },
)
