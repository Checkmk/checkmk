#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"


# oid(".1.3.6.1.4.1.9.9.109.1.1.1.1.5.1") is depreceated by
# oid(".1.3.6.1.4.1.9.9.109.1.1.1.1.8.1"), we recognize both for now


from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.agent_based.v2 import (
    all_of,
    any_of,
    contains,
    exists,
    not_contains,
    not_exists,
    render,
    SNMPTree,
    StringTable,
)

check_info = dict[str, LegacyCheckDefinition]()


def discover_cisco_cpu(info):
    if info and (info[0][0].isdigit() or info[0][1].isdigit()):
        yield None, {}


def check_cisco_cpu(item, params, info):
    # Value of info could be (None, None) or ("", "").
    if not info[0][0].isdigit() and not info[0][1].isdigit():
        return 3, "No information about the CPU utilization available"

    if info[0][1]:
        util = float(info[0][1])
    else:
        util = float(info[0][0])

    warn, crit = params.get("util", (None, None)) if isinstance(params, dict) else params

    return check_levels(
        util,
        "util",
        (warn, crit),
        human_readable_func=render.percent,
        boundaries=(0, 100),
        infoname="Utilization in the last 5 minutes",
    )


def parse_cisco_cpu(string_table: StringTable) -> StringTable:
    return string_table


check_info["cisco_cpu"] = LegacyCheckDefinition(
    name="cisco_cpu",
    parse_function=parse_cisco_cpu,
    detect=all_of(
        contains(".1.3.6.1.2.1.1.1.0", "cisco"),
        any_of(
            not_contains(".1.3.6.1.2.1.1.1.0", "nx-os"), not_exists(".1.3.6.1.4.1.9.9.305.1.1.1.0")
        ),
        not_exists(".1.3.6.1.4.1.9.9.109.1.1.1.1.2.*"),
        any_of(
            exists(".1.3.6.1.4.1.9.9.109.1.1.1.1.8.1"), exists(".1.3.6.1.4.1.9.9.109.1.1.1.1.5.1")
        ),
    ),
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.9.9.109.1.1.1.1",
        oids=["5", "8"],
    ),
    service_name="CPU utilization",
    discovery_function=discover_cisco_cpu,
    check_function=check_cisco_cpu,
    check_ruleset_name="cpu_utilization",
    check_default_parameters={"util": (80.0, 90.0)},
)
