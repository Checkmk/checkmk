#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import check_levels, LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.liebert import DETECT_LIEBERT, parse_liebert_float


def check_liebert_fans_condenser(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    levels = params["levels"] + params.get("levels_lower", (None, None))
    yield check_levels(data[0], "filehandler_perc", levels, unit=data[1])


def discover_liebert_fans_condenser(section):
    yield from ((item, {}) for item in section)


check_info["liebert_fans_condenser"] = LegacyCheckDefinition(
    detect=DETECT_LIEBERT,
    parse_function=parse_liebert_float,
    discovery_function=discover_liebert_fans_condenser,
    check_function=check_liebert_fans_condenser,
    service_name="%s",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.476.1.42.3.9.20.1",
        oids=["10.1.2.1.5276", "20.1.2.1.5276", "30.1.2.1.5276"],
    ),
    check_ruleset_name="hw_fans_perc",
    check_default_parameters={
        "levels": (80, 90),
    },
)
