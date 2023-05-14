#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated"

from cmk.base.check_api import discover, LegacyCheckDefinition, startswith
from cmk.base.check_legacy_includes.cpu_util import check_cpu_util
from cmk.base.config import check_info, factory_settings
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree

factory_settings["aruba_cpu_util_default_levels"] = {
    "levels": (80.0, 90.0),
}


def parse_aruba_cpu_util(info):
    parsed = {}
    for description, raw_cpu_util in info:
        try:
            parsed.setdefault(description, float(raw_cpu_util))
        except ValueError:
            pass
    return parsed


# no get_parsed_item_data because the cpu utilization can be exactly 0 for some devices, which would
# result in "UNKN - Item not found in monitoring data", because parsed[item] evaluates to False
def check_aruba_cpu_util(item, params, parsed):
    measured_cpu_util = parsed.get(item)
    if measured_cpu_util is None:
        return None
    return check_cpu_util(measured_cpu_util, params)


check_info["aruba_cpu_util"] = LegacyCheckDefinition(
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.14823"),
    parse_function=parse_aruba_cpu_util,
    check_function=check_aruba_cpu_util,
    discovery_function=discover(),
    service_name="CPU utilization %s",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.14823.2.2.1.1.1.9.1",
        oids=["2", "3"],
    ),
    check_ruleset_name="cpu_utilization_multiitem",
    default_levels_variable="aruba_cpu_util_default_levels",
)
