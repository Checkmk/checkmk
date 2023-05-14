#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.base.check_api import check_levels, get_percent_human_readable, LegacyCheckDefinition
from cmk.base.config import check_info
from cmk.base.plugins.agent_based.agent_based_api.v1 import SNMPTree
from cmk.base.plugins.agent_based.utils.sophos import DETECT_SOPHOS


def parse_sophos_memory(info):
    try:
        return int(info[0][0])
    except (ValueError, IndexError):
        return None


def check_sophos_memory(_item, params, parsed):
    return check_levels(
        parsed,
        "memory_util",
        params.get("memory_levels", (None, None)),
        infoname="Usage",
        human_readable_func=get_percent_human_readable,
    )


check_info["sophos_memory"] = LegacyCheckDefinition(
    detect=DETECT_SOPHOS,
    parse_function=parse_sophos_memory,
    discovery_function=lambda parsed: [(None, {})] if parsed is not None else None,
    check_function=check_sophos_memory,
    service_name="Memory",
    check_ruleset_name="sophos_memory",
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.21067.2.1.2.4",
        oids=["2"],
    ),
)
