#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time

from cmk.base.check_api import check_levels, get_rate, LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import any_of, equals, OIDEnd, SNMPTree

aironet_default_error_levels = (1.0, 10.0)  # per second


def inventory_aironet_errors(info):
    yield from ((line[0], aironet_default_error_levels) for line in info)


def check_aironet_errors(item, params, info):
    for line in info:
        if line[0] == item:
            value = int(line[1])
            this_time = time.time()
            yield check_levels(
                get_rate("aironet_errors.%s" % item, this_time, value),
                "errors",
                params,
                infoname="Errors/s",
            )
            return


check_info["aironet_errors"] = LegacyCheckDefinition(
    detect=any_of(
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9.1.525"),
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9.1.618"),
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9.1.685"),
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9.1.758"),
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9.1.1034"),
        equals(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.9.1.1247"),
    ),
    check_function=check_aironet_errors,
    discovery_function=inventory_aironet_errors,
    service_name="MAC CRC errors radio %s",
    # CISCO-DOT11-IF-MIB::cd11IfRecFrameMacCrcErrors
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9.9.272.1.2.1.1.1",
        oids=[OIDEnd(), "2"],
    ),
)
