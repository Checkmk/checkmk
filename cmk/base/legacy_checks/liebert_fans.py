#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import check_levels, discover, get_parsed_item_data, LegacyCheckDefinition
from cmk.base.check_legacy_includes.liebert import parse_liebert_wrapper
from cmk.base.config import check_info, factory_settings
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.liebert import DETECT_LIEBERT

# example output
# .1.3.6.1.4.1.476.1.42.3.9.20.1.10.1.2.1.5077 Fan Speed
# .1.3.6.1.4.1.476.1.42.3.9.20.1.20.1.2.1.5077 0
# .1.3.6.1.4.1.476.1.42.3.9.20.1.30.1.2.1.5077 %

factory_settings["liebert_fans_default_levels"] = {
    "levels": (80, 90),
}


@get_parsed_item_data
def check_liebert_fans(_item, params, data):
    levels = params["levels"] + params.get("levels_lower", (None, None))
    yield check_levels(data[0], "filehandler_perc", levels, unit=data[1])


check_info["liebert_fans"] = LegacyCheckDefinition(
    detect=DETECT_LIEBERT,
    parse_function=parse_liebert_wrapper,
    discovery_function=discover(),
    check_function=check_liebert_fans,
    service_name="%s",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.476.1.42.3.9.20.1",
        oids=["10.1.2.1.5077", "20.1.2.1.5077", "30.1.2.1.5077"],
    ),
    check_ruleset_name="hw_fans_perc",
    default_levels_variable="liebert_fans_default_levels",
)
