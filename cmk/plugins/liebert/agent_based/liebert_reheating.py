#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping
from typing import Any

from cmk.agent_based.v1 import (
    check_levels as check_levels_v1,  # we can only use v2 after migrating the ruleset!
)
from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Service,
    SimpleSNMPSection,
    SNMPTree,
)
from cmk.plugins.liebert.agent_based.lib import DETECT_LIEBERT, parse_liebert_float, Section

# example output
# .1.3.6.1.4.1.476.1.42.3.9.20.1.10.1.2.1.5080 Reheat Utilization
# .1.3.6.1.4.1.476.1.42.3.9.20.1.20.1.2.1.5080 0
# .1.3.6.1.4.1.476.1.42.3.9.20.1.30.1.2.1.5080 %


def inventory_liebert_reheating(section: Section[float]) -> DiscoveryResult:
    if any("Reheat" in key for key in section):
        yield Service()


def check_liebert_reheating(params: Mapping[str, Any], section: Section[float]) -> CheckResult:
    if (data := next((e for k, e in section.items() if "Reheat" in k), None)) is None:
        return
    value, unit = data
    yield from check_levels_v1(
        value,
        metric_name="fan_perc",
        levels_upper=params["levels"],
        render_func=lambda x: f"{x:.2f} {unit}",
    )


snmp_section_liebert_reheating = SimpleSNMPSection(
    name="liebert_reheating",
    detect=DETECT_LIEBERT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.476.1.42.3.9.20.1",
        oids=["10.1.2.1.5080", "20.1.2.1.5080", "30.1.2.1.5080"],
    ),
    parse_function=parse_liebert_float,
)
check_plugin_liebert_reheating = CheckPlugin(
    name="liebert_reheating",
    service_name="Reheating Utilization",
    discovery_function=inventory_liebert_reheating,
    check_function=check_liebert_reheating,
    check_default_parameters={
        "levels": (80, 90),
    },
)
