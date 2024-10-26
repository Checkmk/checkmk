#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_legacy_includes.cpu_util import check_cpu_util
from cmk.base.check_legacy_includes.huawei_switch import parse_huawei_physical_entity_values

from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import OIDEnd, SNMPTree
from cmk.plugins.lib.huawei import DETECT_HUAWEI_SWITCH

check_info = {}


def parse_huawei_switch_cpu(string_table):
    return parse_huawei_physical_entity_values(string_table)


def check_huawei_switch_cpu(item, params, parsed):
    if not (item_data := parsed.get(item)):
        return
    try:
        util = float(item_data.value)
    except TypeError:
        return
    yield from check_cpu_util(util, params, cores=[("core1", util)])


def discover_huawei_switch_cpu(section):
    yield from ((item, {}) for item in section)


check_info["huawei_switch_cpu"] = LegacyCheckDefinition(
    name="huawei_switch_cpu",
    detect=DETECT_HUAWEI_SWITCH,
    fetch=[
        SNMPTree(
            base=".1.3.6.1.2.1.47.1.1.1.1",
            oids=[OIDEnd(), "7"],
        ),
        SNMPTree(
            base=".1.3.6.1.4.1.2011.5.25.31.1.1.1.1",
            oids=[OIDEnd(), "5"],
        ),
    ],
    parse_function=parse_huawei_switch_cpu,
    service_name="CPU utilization %s",
    discovery_function=discover_huawei_switch_cpu,
    check_function=check_huawei_switch_cpu,
    check_ruleset_name="cpu_utilization_multiitem",
    check_default_parameters={
        "levels": (80.0, 90.0),
    },
)
