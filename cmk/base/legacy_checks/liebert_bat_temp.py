#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import LegacyCheckDefinition
from cmk.base.check_legacy_includes.temperature import check_temperature
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.lgp import DETECT_LGP

liebert_bat_temp_default = (40, 50)  # warning / critical


def parse_liebert_bat_temp(string_table):
    try:
        return {"Battery": int(string_table[0][0])}
    except (ValueError, IndexError):
        return {}


def discover_liebert_bat_temp(section):
    yield from ((key, liebert_bat_temp_default) for key in section)


def check_liebert_bat_temp(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    yield check_temperature(data, params, "liebert_bat_temp_%s" % item)


check_info["liebert_bat_temp"] = LegacyCheckDefinition(
    detect=DETECT_LGP,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.476.1.42.3.4.1.3.3.1.3",
        oids=["1"],
    ),
    parse_function=parse_liebert_bat_temp,
    service_name="Temperature %s",
    discovery_function=discover_liebert_bat_temp,
    check_function=check_liebert_bat_temp,
    check_ruleset_name="temperature",
)
