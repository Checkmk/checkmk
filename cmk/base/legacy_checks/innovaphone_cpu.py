#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


from cmk.agent_based.legacy.v0_unstable import LegacyCheckDefinition
from cmk.agent_based.v2 import StringTable
from cmk.base.check_legacy_includes.cpu_util import check_cpu_util

check_info = {}


def saveint(i: str) -> int:
    """Tries to cast a string to an integer and return it. In case this
    fails, it returns 0.

    Advice: Please don't use this function in new code. It is understood as
    bad style these days, because in case you get 0 back from this function,
    you can not know whether it is really 0 or something went wrong."""
    try:
        return int(i)
    except (TypeError, ValueError):
        return 0


def discover_innovaphone_cpu(info):
    yield None, {}


def check_innovaphone_cpu(_no_item, params, info):
    usage = saveint(info[0][1])
    return check_cpu_util(usage, params)


def parse_innovaphone_cpu(string_table: StringTable) -> StringTable:
    return string_table


check_info["innovaphone_cpu"] = LegacyCheckDefinition(
    name="innovaphone_cpu",
    parse_function=parse_innovaphone_cpu,
    service_name="CPU utilization",
    discovery_function=discover_innovaphone_cpu,
    check_function=check_innovaphone_cpu,
    check_ruleset_name="cpu_utilization",
    check_default_parameters={"util": (90.0, 95.0)},
)
