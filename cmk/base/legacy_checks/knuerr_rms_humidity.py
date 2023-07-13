#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.humidity import check_humidity
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.knuerr import DETECT_KNUERR

knuerr_rms_humidity_default_levels = (30, 40, 70, 75)


def inventory_knuerr_rms_humidity(info):
    return [(None, knuerr_rms_humidity_default_levels)]


def check_knuerr_rms_humidity(_no_item, params, info):
    _name, reading = info[0]
    return check_humidity(float(reading) / 10, params)


check_info["knuerr_rms_humidity"] = LegacyCheckDefinition(
    detect=DETECT_KNUERR,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.3711.15.1.1.1.2",
        oids=["2", "4"],
    ),
    service_name="Humidity",
    discovery_function=inventory_knuerr_rms_humidity,
    check_function=check_knuerr_rms_humidity,
    check_ruleset_name="single_humidity",
)
