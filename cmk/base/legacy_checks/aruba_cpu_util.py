#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


# mypy: disable-error-code="var-annotated"

from cmk.base.check_legacy_includes.cpu_util import check_cpu_util

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import SNMPTree, startswith

check_info = {}


def parse_aruba_cpu_util(string_table):
    parsed = {}
    for description, raw_cpu_util in string_table:
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


def discover_aruba_cpu_util(section):
    yield from ((item, {}) for item in section)


check_info["aruba_cpu_util"] = LegacyCheckDefinition(
    name="aruba_cpu_util",
    detect=startswith(".1.3.6.1.2.1.1.2.0", ".1.3.6.1.4.1.14823"),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.14823.2.2.1.1.1.9.1",
        oids=["2", "3"],
    ),
    parse_function=parse_aruba_cpu_util,
    service_name="CPU utilization %s",
    discovery_function=discover_aruba_cpu_util,
    check_function=check_aruba_cpu_util,
    check_ruleset_name="cpu_utilization_multiitem",
    check_default_parameters={
        "levels": (80.0, 90.0),
    },
)
