#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any, NamedTuple

from cmk.agent_based.v2 import (
    CheckPlugin,
    CheckResult,
    DiscoveryResult,
    Metric,
    render,
    Result,
    Service,
    SimpleSNMPSection,
    SNMPTree,
    State,
    StringTable,
)
from cmk.plugins.juniper.lib import DETECT_JUNIPER_TRPZ


class Section(NamedTuple):
    used: float
    total: float


def parse_juniper_trpz_flash(string_table: StringTable) -> Section | None:
    if not string_table:
        return None
    used, total = string_table[0]
    return Section(used=float(used), total=float(total))


def discover_juniper_trpz_flash(section: Section) -> DiscoveryResult:
    yield Service()


def check_juniper_trpz_flash(params: Mapping[str, Any], section: Section) -> CheckResult:
    warn, crit = params["levels"]
    message = f"Used: {render.bytes(section.used)} of {render.bytes(section.total)} "
    perc_used = (section.used / section.total) * 100
    if isinstance(crit, float):
        a_warn = (warn / 100.0) * section.total
        a_crit = (crit / 100.0) * section.total
        levels = f"Levels Warn/Crit are ({warn:.2f}%, {crit:.2f}%)"
        if perc_used > crit:
            yield Result(state=State.CRIT, summary=message + levels)
        elif perc_used > warn:
            yield Result(state=State.WARN, summary=message + levels)
        else:
            yield Result(state=State.OK, summary=message)
        yield Metric("used", section.used, levels=(a_warn, a_crit), boundaries=(0, section.total))
    else:
        levels = f"Levels Warn/Crit are ({render.bytes(warn)}, {render.bytes(crit)})"
        if section.used > crit:
            yield Result(state=State.CRIT, summary=message + levels)
        elif section.used > warn:
            yield Result(state=State.WARN, summary=message + levels)
        else:
            yield Result(state=State.OK, summary=message)
        yield Metric(
            "used",
            section.used,
            levels=(float(warn), float(crit)),
            boundaries=(0, section.total),
        )


snmp_section_juniper_trpz_flash = SimpleSNMPSection(
    name="juniper_trpz_flash",
    detect=DETECT_JUNIPER_TRPZ,
    fetch=SNMPTree(
        base=".1.3.6.1.4.1.14525.4.8.1.1",
        oids=["3", "4"],
    ),
    parse_function=parse_juniper_trpz_flash,
)


check_plugin_juniper_trpz_flash = CheckPlugin(
    name="juniper_trpz_flash",
    service_name="Flash",
    discovery_function=discover_juniper_trpz_flash,
    check_function=check_juniper_trpz_flash,
    check_ruleset_name="general_flash_usage",
    check_default_parameters={"levels": (90.0, 95.0)},
)
