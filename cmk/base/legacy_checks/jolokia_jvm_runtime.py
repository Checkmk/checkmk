#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import discover, get_parsed_item_data, LegacyCheckDefinition
from cmk.base.check_legacy_includes.jolokia import parse_jolokia_json_output
from cmk.base.check_legacy_includes.uptime import check_uptime_seconds
from cmk.base.config import check_info


def parse_jolokia_jvm_runtime(info):
    return {instance: json_data for instance, _mbean, json_data in parse_jolokia_json_output(info)}


@get_parsed_item_data
def check_jolokia_jvm_runtime_uptime(_item, params, data):
    milli_uptime = data.get("Uptime")
    if milli_uptime is None:
        return None
    return check_uptime_seconds(params, milli_uptime / 1000.0)


check_info["jolokia_jvm_runtime"] = LegacyCheckDefinition(
    parse_function=parse_jolokia_jvm_runtime,
    discovery_function=discover(),
    check_function=check_jolokia_jvm_runtime_uptime,
    service_name="JVM %s Uptime",
    check_ruleset_name="jvm_uptime",
)
