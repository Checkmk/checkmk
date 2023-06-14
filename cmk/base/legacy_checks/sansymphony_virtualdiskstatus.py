#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# <<<sansymphony_virtualdiskstatus>>>
# testvmfs01 Online
# vmfs10 Online


# mypy: disable-error-code="var-annotated"

from cmk.base.check_api import discover, get_parsed_item_data, LegacyCheckDefinition
from cmk.base.config import check_info


def parse_sansymphony_virtualdiskstatus(info):
    parsed = {}
    for line in info:
        parsed.setdefault(line[0], " ".join(line[1:]))
    return parsed


@get_parsed_item_data
def check_sansymphony_virtualdiskstatus(_no_item, _no_params, data):
    state = 0 if data == "Online" else 2
    return state, "Volume state is: %s" % data


check_info["sansymphony_virtualdiskstatus"] = LegacyCheckDefinition(
    parse_function=parse_sansymphony_virtualdiskstatus,
    discovery_function=discover(),
    check_function=check_sansymphony_virtualdiskstatus,
    service_name="sansymphony Virtual Disk %s",
)
