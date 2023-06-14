#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import discover, get_parsed_item_data, LegacyCheckDefinition
from cmk.base.check_legacy_includes.fan import check_fan
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import OIDEnd, SNMPTree
from cmk.base.plugins.agent_based.utils.qnap import DETECT_QNAP


def parse_qnap_fans(info):
    parsed = {}
    for fan, value in info:
        try:
            parsed[fan] = int(value.replace("RPM", ""))
        except ValueError:
            pass
    return parsed


@get_parsed_item_data
def check_qnap_fans(_item, params, data):
    return check_fan(data, params)


check_info["qnap_fans"] = LegacyCheckDefinition(
    detect=DETECT_QNAP,
    discovery_function=discover(),
    parse_function=parse_qnap_fans,
    check_function=check_qnap_fans,
    service_name="QNAP FAN %s",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.24681.1.2.15.1",
        oids=[OIDEnd(), "3"],
    ),
    check_ruleset_name="hw_fans",
    check_default_parameters={
        "upper": (None, None),
        "lower": (2000, 1000),
    },
)
