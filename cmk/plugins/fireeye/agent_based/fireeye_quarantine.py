#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.agent_based.v2 import (
    check_levels,
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    render,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.fireeye.lib import DETECT

# .1.3.6.1.4.1.25597.13.1.40.0 1

type Section = StringTable


def discover_fireeye_quarantine(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


def check_fireeye_quarantine(
    params: Mapping[str, tuple[float, float] | None], section: Section
) -> CheckResult:
    usage = int(section[0][0])
    yield from check_levels(
        usage,
        metric_name="quarantine",
        levels_upper=("fixed", levels) if (levels := params["usage"]) else ("no_levels", None),
        render_func=render.percent,
        label="Usage",
    )


def parse_fireeye_quarantine(string_table: StringTable) -> Section:
    return string_table


snmp_section_fireeye_quarantine = SimpleSNMPSection(
    name="fireeye_quarantine",
    parse_function=parse_fireeye_quarantine,
    detect=DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.25597.13.1.40",
        oids=["0"],
    ),
)


check_plugin_fireeye_quarantine = CheckPlugin(
    name="fireeye_quarantine",
    service_name="Quarantine Usage",
    discovery_function=discover_fireeye_quarantine,
    check_function=check_fireeye_quarantine,
    check_ruleset_name="fireeye_quarantine",
    check_default_parameters={"usage": (70, 80)},
)
