#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time
from collections.abc import Iterable

from cmk.base.check_api import check_levels, get_age_human_readable, LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.systemtime import Section


def discover_systemtime(section: Section) -> Iterable[tuple[None, dict]]:
    if section:
        yield None, {}


def check_systemtime(item, params, parsed):
    if not parsed:
        return

    systemtime = parsed["foreign_systemtime"]
    if "our_systemtime" in parsed:
        offset = systemtime - parsed["our_systemtime"]
    else:
        offset = systemtime - time.time()

    warn, crit = params if isinstance(params, tuple) else params["levels"]
    yield check_levels(
        offset,
        "offset",
        (warn, crit, -warn, -crit),
        human_readable_func=get_age_human_readable,
        infoname="Offset",
    )


check_info["systemtime"] = LegacyCheckDefinition(
    check_function=check_systemtime,
    discovery_function=discover_systemtime,
    service_name="System Time",
    check_ruleset_name="systemtime",
    check_default_parameters={"levels": (30, 60)},
)
