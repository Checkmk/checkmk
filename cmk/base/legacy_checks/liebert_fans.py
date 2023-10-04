#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import check_levels, LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.liebert import DETECT_LIEBERT, parse_liebert_float

# example output
# .1.3.6.1.4.1.476.1.42.3.9.20.1.10.1.2.1.5077 Fan Speed
# .1.3.6.1.4.1.476.1.42.3.9.20.1.20.1.2.1.5077 0
# .1.3.6.1.4.1.476.1.42.3.9.20.1.30.1.2.1.5077 %


def check_liebert_fans(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    levels = params["levels"] + params.get("levels_lower", (None, None))
    yield check_levels(data[0], "filehandler_perc", levels, unit=data[1])


def discover_liebert_fans(section):
    yield from ((item, {}) for item in section)


check_info["liebert_fans"] = LegacyCheckDefinition(
    detect=DETECT_LIEBERT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.476.1.42.3.9.20.1",
        oids=["10.1.2.1.5077", "20.1.2.1.5077", "30.1.2.1.5077"],
    ),
    parse_function=parse_liebert_float,
    service_name="%s",
    discovery_function=discover_liebert_fans,
    check_function=check_liebert_fans,
    check_ruleset_name="hw_fans_perc",
    check_default_parameters={
        "levels": (80, 90),
    },
)
