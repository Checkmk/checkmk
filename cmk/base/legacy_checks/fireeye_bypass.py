#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.fireeye import DETECT

# .1.3.6.1.4.1.25597.13.1.41.0 0
# .1.3.6.1.4.1.25597.13.1.42.0 0
# .1.3.6.1.4.1.25597.13.1.43.0 0


def inventory_bypass(info):
    value = int(info[0][0])
    yield None, {"value": value}


def check_fireeye_bypass(_no_item, params, info):
    expected_value = params.get("value", 0)
    current_value = int(info[0][0])
    yield 0, "Bypass E-Mail count: %d" % current_value
    if current_value != expected_value:
        yield 2, " (was %d before)" % expected_value


check_info["fireeye_bypass"] = LegacyCheckDefinition(
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.25597.13.1",
        oids=["41"],
    ),
    service_name="Bypass Mail Rate",
    discovery_function=inventory_bypass,
    check_function=check_fireeye_bypass,
)
