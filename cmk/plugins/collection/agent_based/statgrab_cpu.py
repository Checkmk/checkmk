#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import time
from collections.abc import Mapping

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    get_value_store,
    Service,
    StringTable,
)
from cmk.plugins.lib.cpu_util import check_cpu_util_unix, CPUInfo


def parse_statgrab_cpu(string_table: StringTable) -> CPUInfo | None:
    raw = {k: int(v) for k, v in string_table}
    if not raw:
        return None
    return CPUInfo(
        "cpu",
        raw.get("user", 0),
        raw.get("nice", 0),
        raw.get("kernel", 0),
        raw.get("idle", 0),
        raw.get("iowait", 0),
    )


def inventory_statgrab_cpu(section: CPUInfo) -> DiscoveryResult:
    yield Service()


def check_statgrab_cpu(params: Mapping[str, object], section: CPUInfo) -> CheckResult:
    yield from check_cpu_util_unix(
        cpu_info=section,
        params=params,
        this_time=time.time(),
        value_store=get_value_store(),
        cores=(),
        values_counter=True,
    )


agent_section_statgrab_cpu = AgentSection(
    name="statgrab_cpu",
    parse_function=parse_statgrab_cpu,
)

check_plugin_statgrab_cpu = CheckPlugin(
    name="statgrab_cpu",
    service_name="CPU utilization",
    discovery_function=inventory_statgrab_cpu,
    check_function=check_statgrab_cpu,
    check_ruleset_name="cpu_iowait",
    check_default_parameters={},
)
