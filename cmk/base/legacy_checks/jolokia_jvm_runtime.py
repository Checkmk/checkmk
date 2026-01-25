#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"


import time
from datetime import timedelta

from cmk.agent_based.legacy.v0_unstable import check_levels, LegacyCheckDefinition
from cmk.base.check_legacy_includes.jolokia import parse_jolokia_json_output

check_info = {}


def parse_jolokia_jvm_runtime(string_table):
    return {
        instance: json_data
        for instance, _mbean, json_data in parse_jolokia_json_output(string_table)
    }


def check_jolokia_jvm_runtime_uptime(item, params, parsed):
    if not (data := parsed.get(item)):
        return
    milli_uptime = data.get("Uptime")
    if milli_uptime is None:
        return
    uptime_sec = milli_uptime / 1000.0

    params = params.get("max", (None, None)) + params.get("min", (None, None))
    yield check_levels(
        uptime_sec,
        "uptime",
        params,
        human_readable_func=lambda x: timedelta(seconds=int(x)),
        infoname="Up since %s, uptime"
        % time.strftime("%c", time.localtime(time.time() - uptime_sec)),
    )


def discover_jolokia_jvm_runtime(section):
    yield from ((item, {}) for item in section)


check_info["jolokia_jvm_runtime"] = LegacyCheckDefinition(
    name="jolokia_jvm_runtime",
    parse_function=parse_jolokia_jvm_runtime,
    service_name="JVM %s Uptime",
    discovery_function=discover_jolokia_jvm_runtime,
    check_function=check_jolokia_jvm_runtime_uptime,
    check_ruleset_name="jvm_uptime",
)
