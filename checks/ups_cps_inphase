#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

from cmk.base.check_legacy_includes.elphase import check_elphase
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.ups import DETECT_UPS_CPS


def parse_ups_cps_inphase(info: list[str]) -> dict[Literal["1"], dict[str, float]]:
    parsed = {}
    for index, stat_name in enumerate(("voltage", "frequency")):
        try:
            parsed[stat_name] = float(info[0][index]) / 10
        except ValueError:
            continue

    return {"1": parsed} if parsed else {}


def inventory_ups_cps_inphase(parsed):
    if parsed:
        yield "1", {}


check_info["ups_cps_inphase"] = {
    "detect": DETECT_UPS_CPS,
    "parse_function": parse_ups_cps_inphase,
    "discovery_function": inventory_ups_cps_inphase,
    "check_function": check_elphase,
    "service_name": "UPS Input Phase %s",
    "fetch": SNMPTree(
        base=".1.3.6.1.4.1.3808.1.1.1.3.2",
        oids=["1", "4"],
    ),
    "check_ruleset_name": "el_inphase",
}
