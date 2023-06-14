#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import discover, get_parsed_item_data, LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.liebert import (
    DETECT_LIEBERT,
    parse_liebert_str_without_unit,
)

# example output
# .1.3.6.1.4.1.476.1.42.3.9.20.1.10.1.2.1.5302 Free Cooling Status
# .1.3.6.1.4.1.476.1.42.3.9.20.1.20.1.2.1.5302 off

check_info["liebert_cooling_status"] = LegacyCheckDefinition(
    detect=DETECT_LIEBERT,
    parse_function=parse_liebert_str_without_unit,
    discovery_function=discover(),
    check_function=get_parsed_item_data(lambda _item, _no_params, data: (0, data)),
    service_name="%s",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.476.1.42.3.9.20.1",
        oids=["10.1.2.1.5302", "20.1.2.1.5302"],
    ),
)
