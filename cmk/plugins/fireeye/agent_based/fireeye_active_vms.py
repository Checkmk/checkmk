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
    Service,
    SimpleSNMPSection,
    SNMPTree,
    StringTable,
)
from cmk.plugins.fireeye import lib as fireeye

type Section = StringTable


def discover_fireeye_active_vms(section: Section) -> DiscoveryResult:
    if section:
        yield Service()


def check_fireeye_active_vms(
    params: Mapping[str, tuple[float, float] | None], section: Section
) -> CheckResult:
    value = int(section[0][0])
    yield from check_levels(
        value,
        metric_name="active_vms",
        levels_upper=("fixed", levels) if (levels := params["vms"]) else ("no_levels", None),
        render_func=str,
        label="Active VMs",
    )


def parse_fireeye_active_vms(string_table: StringTable) -> Section:
    return string_table


snmp_section_fireeye_active_vms = SimpleSNMPSection(
    name="fireeye_active_vms",
    detect=fireeye.DETECT,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.25597.11.5.1.9",
        oids=["0"],
    ),
    parse_function=parse_fireeye_active_vms,
)


check_plugin_fireeye_active_vms = CheckPlugin(
    name="fireeye_active_vms",
    service_name="Active VMs",
    discovery_function=discover_fireeye_active_vms,
    check_function=check_fireeye_active_vms,
    check_ruleset_name="fireeye_active_vms",
    check_default_parameters={"vms": (100, 120)},
)
