#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import Iterable

from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.ups_out_voltage import check_ups_out_voltage
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import OIDEnd, SNMPTree
from cmk.base.plugins.agent_based.utils.ups import DETECT_UPS_GENERIC


def discover_ups_out_voltage(info: list[list[str]]) -> Iterable[tuple[str, dict]]:
    yield from ((item, {}) for item, value, *_rest in info if int(value) > 0)


check_info["ups_out_voltage"] = LegacyCheckDefinition(
    detect=DETECT_UPS_GENERIC,
    fetch=SNMPTree(
        base=".1.3.6.1.2.1.33.1.4.4.1",
        oids=[OIDEnd(), "2"],
    ),
    service_name="OUT voltage phase %s",
    discovery_function=discover_ups_out_voltage,
    check_function=check_ups_out_voltage,
    check_ruleset_name="evolt",
    check_default_parameters={
        "levels_lower": (210.0, 180.0),
    },
)
