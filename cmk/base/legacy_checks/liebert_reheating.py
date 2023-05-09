#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import check_levels
from cmk.base.check_legacy_includes.liebert import parse_liebert_wrapper
from cmk.base.config import check_info, factory_settings
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.liebert import DETECT_LIEBERT

# example output
# .1.3.6.1.4.1.476.1.42.3.9.20.1.10.1.2.1.5080 Reheat Utilization
# .1.3.6.1.4.1.476.1.42.3.9.20.1.20.1.2.1.5080 0
# .1.3.6.1.4.1.476.1.42.3.9.20.1.30.1.2.1.5080 %

factory_settings["liebert_reheating_default_levels"] = {
    "levels": (80, 90),
}


def inventory_liebert_reheating(parsed):
    if any("Reheat" in key for key in parsed):
        yield None, {}


def check_liebert_reheating(_no_item, params, parsed):
    for key, (value, unit) in parsed.items():
        if "Reheat" not in key:
            continue
        yield check_levels(value, "filehandler_perc", params["levels"], unit=unit)


check_info["liebert_reheating"] = {
    "detect": DETECT_LIEBERT,
    "parse_function": parse_liebert_wrapper,
    "discovery_function": inventory_liebert_reheating,
    "check_function": check_liebert_reheating,
    "service_name": "Reheating Utilization",
    "fetch": SNMPTree(
        base=".1.3.6.1.4.1.476.1.42.3.9.20.1",
        oids=["10.1.2.1.5080", "20.1.2.1.5080", "30.1.2.1.5080"],
    ),
    "default_levels_variable": "liebert_reheating_default_levels",
}
